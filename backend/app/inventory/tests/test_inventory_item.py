from django.test import TestCase
from django.utils import timezone
from inventory.models import (
    PhysicalGemstone,
    InventoryItem,
    InventorySource,
    CustodyStatus,
    ListingStatus,
)
from catalog.models import GemstoneSpecies, GemstoneVariety


class InventoryItemSetup(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum", common_name="Sapphire & Ruby", code="COR"
        )
        self.variety = GemstoneVariety.objects.create(
            species=self.species,
            name="Blue Sapphire",
            code="BSAP",
        )
        self.gemstone = PhysicalGemstone.objects.create(
            species=self.species,
            variety=self.variety,
            acquisition_date=timezone.now().date(),
        )

    def make_inventory_item(self, **kwargs):
        defaults = {"physical_gemstone": self.gemstone}
        defaults.update(kwargs)
        return InventoryItem.objects.create(**defaults)


class InventoryItemModelTest(InventoryItemSetup):

    def test_str(self):
        item = self.make_inventory_item()
        self.assertEqual(str(item), f"INV — {self.gemstone.gemstone_id}")

    def test_gemstone_id_property(self):
        item = self.make_inventory_item()
        self.assertEqual(item.gemstone_id, self.gemstone.gemstone_id)

    def test_default_inventory_source(self):
        item = self.make_inventory_item()
        self.assertEqual(item.inventory_source, InventorySource.COMPANY_OWNED)

    def test_default_custody_status(self):
        item = self.make_inventory_item()
        self.assertEqual(item.custody_status, CustodyStatus.IN_HOUSE)

    def test_default_listing_status(self):
        item = self.make_inventory_item()
        self.assertEqual(item.listing_status, ListingStatus.UNLISTED)

    def test_default_flags_are_false(self):
        item = self.make_inventory_item()
        self.assertFalse(item.is_reserved)
        self.assertFalse(item.is_sold)
        self.assertFalse(item.is_certified)
        self.assertFalse(item.is_export_ready)
        self.assertFalse(item.is_delivered)

    def test_one_to_one_relationship(self):
        item = self.make_inventory_item()
        self.assertEqual(item.physical_gemstone, self.gemstone)
        self.assertEqual(self.gemstone.inventory_item, item)

    def test_cannot_create_duplicate_inventory_item_for_same_gemstone(self):
        from django.db import IntegrityError
        self.make_inventory_item()
        with self.assertRaises(IntegrityError):
            InventoryItem.objects.create(physical_gemstone=self.gemstone)

    def test_deleting_gemstone_is_protected(self):
        from django.db.models import ProtectedError
        self.make_inventory_item()
        with self.assertRaises(ProtectedError):
            self.gemstone.delete()


class InventoryItemAvailabilityTest(InventoryItemSetup):

    def test_not_available_when_unlisted(self):
        item = self.make_inventory_item(listing_status=ListingStatus.UNLISTED)
        self.assertFalse(item.is_available)

    def test_available_when_active_and_not_reserved_and_not_sold(self):
        item = self.make_inventory_item(listing_status=ListingStatus.ACTIVE)
        self.assertTrue(item.is_available)

    def test_not_available_when_active_but_reserved(self):
        item = self.make_inventory_item(
            listing_status=ListingStatus.ACTIVE,
            is_reserved=True,
        )
        self.assertFalse(item.is_available)

    def test_not_available_when_active_but_sold(self):
        item = self.make_inventory_item(
            listing_status=ListingStatus.ACTIVE,
            is_sold=True,
        )
        self.assertFalse(item.is_available)

    def test_not_available_when_paused(self):
        item = self.make_inventory_item(listing_status=ListingStatus.PAUSED)
        self.assertFalse(item.is_available)

    def test_not_available_when_archived(self):
        item = self.make_inventory_item(listing_status=ListingStatus.ARCHIVED)
        self.assertFalse(item.is_available)

    def test_availability_updates_when_reserved_flag_changes(self):
        item = self.make_inventory_item(listing_status=ListingStatus.ACTIVE)
        self.assertTrue(item.is_available)
        item.is_reserved = True
        item.save()
        item.refresh_from_db()
        self.assertFalse(item.is_available)

    def test_availability_updates_when_listing_status_changes(self):
        item = self.make_inventory_item(listing_status=ListingStatus.ACTIVE)
        self.assertTrue(item.is_available)
        item.listing_status = ListingStatus.PAUSED
        item.save()
        item.refresh_from_db()
        self.assertFalse(item.is_available)


class InventoryItemAuditFieldsTest(InventoryItemSetup):

    def test_created_at_is_set(self):
        item = self.make_inventory_item()
        self.assertIsNotNone(item.created_at)

    def test_updated_at_changes_on_save(self):
        item = self.make_inventory_item()
        original = item.updated_at
        item.current_location = "Safe B - Drawer 1"
        item.save()
        item.refresh_from_db()
        self.assertGreaterEqual(item.updated_at, original)
