from django.test import TestCase
from django.utils import timezone
from inventory.models import (
    PhysicalGemstone,
    InventoryItem,
    InventoryAuditLog,
    AuditEvent,
    GemstoneLifecycleState,
    ListingStatus,
    CustodyStatus,
)
from inventory.services import (
    transition_gemstone_lifecycle,
    change_listing_status,
    change_custody,
    set_reservation,
    release_reservation,
    mark_sold,
)
from catalog.models import GemstoneSpecies, GemstoneVariety


class AuditTestSetup(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum", common_name="Sapphire & Ruby", code="COR"
        )
        self.variety = GemstoneVariety.objects.create(
            species=self.species, name="Blue Sapphire", code="BSAP"
        )
        self.gemstone = PhysicalGemstone.objects.create(
            species=self.species,
            variety=self.variety,
            acquisition_date=timezone.now().date(),
        )
        self.inventory_item = InventoryItem.objects.create(
            physical_gemstone=self.gemstone,
            listing_status=ListingStatus.ACTIVE,
        )


class InventoryAuditLogModelTest(AuditTestSetup):

    def test_audit_log_is_created(self):
        log = InventoryAuditLog.objects.create(
            physical_gemstone=self.gemstone,
            event=AuditEvent.GEMSTONE_CREATED,
            actor="admin@earthandyou.com",
        )
        self.assertIsNotNone(log.pk)
        self.assertIsNotNone(log.created_at)

    def test_audit_log_str(self):
        log = InventoryAuditLog.objects.create(
            physical_gemstone=self.gemstone,
            event=AuditEvent.GEMSTONE_CREATED,
            actor="system",
        )
        self.assertIn(self.gemstone.gemstone_id, str(log))
        self.assertIn("gemstone_created", str(log))

    def test_audit_log_is_immutable(self):
        log = InventoryAuditLog.objects.create(
            physical_gemstone=self.gemstone,
            event=AuditEvent.GEMSTONE_CREATED,
            actor="system",
        )
        log.actor = "hacker"
        with self.assertRaises(ValueError):
            log.save()

    def test_audit_log_cannot_be_deleted(self):
        log = InventoryAuditLog.objects.create(
            physical_gemstone=self.gemstone,
            event=AuditEvent.GEMSTONE_CREATED,
            actor="system",
        )
        with self.assertRaises(ValueError):
            log.delete()

    def test_audit_log_default_permissions_exclude_add_change_delete(self):
        # default_permissions = ("view",) means add/change/delete are not created
        from django.contrib.auth.models import Permission
        codenames = Permission.objects.filter(
            content_type__app_label="inventory",
            content_type__model="inventoryauditlog",
        ).values_list("codename", flat=True)
        self.assertNotIn("add_inventoryauditlog", codenames)
        self.assertNotIn("change_inventoryauditlog", codenames)
        self.assertNotIn("delete_inventoryauditlog", codenames)


class TransitionGemstoneLifecycleServiceTest(AuditTestSetup):

    def test_valid_transition_creates_audit_log(self):
        log = transition_gemstone_lifecycle(
            self.gemstone,
            GemstoneLifecycleState.TESTED,
            actor="staff@earthandyou.com",
            notes="Initial testing complete",
        )
        self.assertEqual(log.event, AuditEvent.LIFECYCLE_TRANSITION)
        self.assertEqual(log.from_state, GemstoneLifecycleState.ACQUIRED)
        self.assertEqual(log.to_state, GemstoneLifecycleState.TESTED)
        self.assertEqual(log.actor, "staff@earthandyou.com")

    def test_transition_updates_gemstone_state(self):
        transition_gemstone_lifecycle(
            self.gemstone, GemstoneLifecycleState.TESTED
        )
        self.gemstone.refresh_from_db()
        self.assertEqual(self.gemstone.lifecycle_state, GemstoneLifecycleState.TESTED)

    def test_invalid_transition_raises_and_does_not_create_log(self):
        log_count_before = InventoryAuditLog.objects.count()
        with self.assertRaises(ValueError):
            transition_gemstone_lifecycle(
                self.gemstone, GemstoneLifecycleState.DELIVERED
            )
        self.assertEqual(InventoryAuditLog.objects.count(), log_count_before)

    def test_audit_log_is_linked_to_gemstone(self):
        transition_gemstone_lifecycle(
            self.gemstone, GemstoneLifecycleState.TESTED
        )
        self.assertEqual(
            self.gemstone.audit_logs.filter(
                event=AuditEvent.LIFECYCLE_TRANSITION
            ).count(),
            1,
        )


class ChangeListingStatusServiceTest(AuditTestSetup):

    def test_listing_status_change_creates_audit_log(self):
        log = change_listing_status(
            self.inventory_item,
            ListingStatus.PAUSED,
            actor="admin@earthandyou.com",
        )
        self.assertEqual(log.event, AuditEvent.LISTING_STATUS_CHANGED)
        self.assertEqual(log.from_state, ListingStatus.ACTIVE)
        self.assertEqual(log.to_state, ListingStatus.PAUSED)

    def test_listing_status_is_updated(self):
        change_listing_status(self.inventory_item, ListingStatus.PAUSED)
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.listing_status, ListingStatus.PAUSED)


class ChangeCustodyServiceTest(AuditTestSetup):

    def test_custody_change_creates_audit_log(self):
        log = change_custody(
            self.inventory_item,
            CustodyStatus.AT_LABORATORY,
            new_location="GIA Lab",
            actor="staff@earthandyou.com",
        )
        self.assertEqual(log.event, AuditEvent.CUSTODY_CHANGED)
        self.assertEqual(log.from_state, CustodyStatus.IN_HOUSE)
        self.assertEqual(log.to_state, CustodyStatus.AT_LABORATORY)

    def test_custody_and_location_are_updated(self):
        change_custody(
            self.inventory_item,
            CustodyStatus.AT_LABORATORY,
            new_location="GIA Lab",
        )
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.custody_status, CustodyStatus.AT_LABORATORY)
        self.assertEqual(self.inventory_item.current_location, "GIA Lab")


class ReservationServiceTest(AuditTestSetup):

    def test_set_reservation_creates_audit_log(self):
        log = set_reservation(self.inventory_item, actor="customer@example.com")
        self.assertEqual(log.event, AuditEvent.RESERVATION_SET)
        self.assertEqual(log.to_state, "reserved")

    def test_set_reservation_marks_item_reserved(self):
        set_reservation(self.inventory_item)
        self.inventory_item.refresh_from_db()
        self.assertTrue(self.inventory_item.is_reserved)

    def test_cannot_reserve_unavailable_item(self):
        self.inventory_item.listing_status = ListingStatus.PAUSED
        self.inventory_item.save()
        with self.assertRaises(ValueError):
            set_reservation(self.inventory_item)

    def test_cannot_reserve_already_reserved_item(self):
        set_reservation(self.inventory_item)
        with self.assertRaises(ValueError):
            set_reservation(self.inventory_item)

    def test_release_reservation_creates_audit_log(self):
        set_reservation(self.inventory_item)
        log = release_reservation(self.inventory_item, actor="staff@earthandyou.com")
        self.assertEqual(log.event, AuditEvent.RESERVATION_RELEASED)
        self.assertEqual(log.from_state, "reserved")

    def test_release_reservation_clears_reserved_flag(self):
        set_reservation(self.inventory_item)
        release_reservation(self.inventory_item)
        self.inventory_item.refresh_from_db()
        self.assertFalse(self.inventory_item.is_reserved)

    def test_cannot_release_non_reserved_item(self):
        with self.assertRaises(ValueError):
            release_reservation(self.inventory_item)


class MarkSoldServiceTest(AuditTestSetup):

    def test_mark_sold_creates_audit_log(self):
        log = mark_sold(self.inventory_item, actor="staff@earthandyou.com")
        self.assertEqual(log.event, AuditEvent.MARKED_SOLD)

    def test_mark_sold_updates_flags_and_status(self):
        self.inventory_item.is_reserved = True
        self.inventory_item.save()
        mark_sold(self.inventory_item)
        self.inventory_item.refresh_from_db()
        self.assertTrue(self.inventory_item.is_sold)
        self.assertFalse(self.inventory_item.is_reserved)
        self.assertEqual(self.inventory_item.listing_status, ListingStatus.SOLD_OUT)

    def test_cannot_mark_already_sold_item(self):
        mark_sold(self.inventory_item)
        with self.assertRaises(ValueError):
            mark_sold(self.inventory_item)
