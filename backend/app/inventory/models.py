from django.db import models, transaction
from django.utils import timezone
from catalog.models import GemstoneSpecies, GemstoneVariety


class GemstoneLifecycleState(models.TextChoices):
    ACQUIRED = "acquired", "Acquired"
    TESTED = "tested", "Tested"
    CERTIFIED = "certified", "Certified"
    PHOTOGRAPHED = "photographed", "Photographed"
    STORED = "stored", "Stored"
    LISTED = "listed", "Listed"
    RESERVED = "reserved", "Reserved"
    SOLD = "sold", "Sold"
    EXPORTED = "exported", "Exported"
    DELIVERED = "delivered", "Delivered"


LIFECYCLE_TRANSITIONS = {
    GemstoneLifecycleState.ACQUIRED: [
        GemstoneLifecycleState.TESTED,
        GemstoneLifecycleState.STORED,
    ],
    GemstoneLifecycleState.TESTED: [
        GemstoneLifecycleState.CERTIFIED,
        GemstoneLifecycleState.STORED,
    ],
    GemstoneLifecycleState.CERTIFIED: [
        GemstoneLifecycleState.PHOTOGRAPHED,
        GemstoneLifecycleState.STORED,
    ],
    GemstoneLifecycleState.PHOTOGRAPHED: [
        GemstoneLifecycleState.STORED,
        GemstoneLifecycleState.LISTED,
    ],
    GemstoneLifecycleState.STORED: [
        GemstoneLifecycleState.TESTED,
        GemstoneLifecycleState.CERTIFIED,
        GemstoneLifecycleState.PHOTOGRAPHED,
        GemstoneLifecycleState.LISTED,
    ],
    GemstoneLifecycleState.LISTED: [
        GemstoneLifecycleState.RESERVED,
        GemstoneLifecycleState.STORED,
    ],
    GemstoneLifecycleState.RESERVED: [
        GemstoneLifecycleState.LISTED,
        GemstoneLifecycleState.SOLD,
    ],
    GemstoneLifecycleState.SOLD: [
        GemstoneLifecycleState.EXPORTED,
    ],
    GemstoneLifecycleState.EXPORTED: [
        GemstoneLifecycleState.DELIVERED,
    ],
    GemstoneLifecycleState.DELIVERED: [],
}


class GemstoneIDSequence(models.Model):
    """
    Tracks the last used sequence number per species per year.
    Used to generate unique gemstone IDs atomically.
    """

    species_code = models.CharField(max_length=10)
    year = models.PositiveSmallIntegerField()
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["species_code", "year"],
                name="unique_sequence_per_species_per_year",
            )
        ]

    def __str__(self):
        return f"CEY-{self.species_code}-{self.year}-{self.last_sequence:06d}"


class PhysicalGemstone(models.Model):
    """
    Represents a single real-world physical gemstone.

    ID format: CEY-{SPECIES_CODE}-{YEAR}-{SEQUENCE:06d}
    Example:   CEY-COR-2026-000001
    """

    gemstone_id = models.CharField(max_length=30, unique=True, editable=False)
    species = models.ForeignKey(
        GemstoneSpecies,
        on_delete=models.PROTECT,
        related_name="physical_gemstones",
    )
    variety = models.ForeignKey(
        GemstoneVariety,
        on_delete=models.PROTECT,
        related_name="physical_gemstones",
        null=True,
        blank=True,
        help_text="Optional — variety may not be determined at acquisition",
    )
    lifecycle_state = models.CharField(
        max_length=20,
        choices=GemstoneLifecycleState.choices,
        default=GemstoneLifecycleState.ACQUIRED,
    )
    acquisition_date = models.DateField()
    acquisition_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Physical Gemstone"
        verbose_name_plural = "Physical Gemstones"
        ordering = ["-created_at"]

    def __str__(self):
        return self.gemstone_id

    def save(self, *args, **kwargs):
        if not self.gemstone_id:
            self.gemstone_id = self.generate_id_for_species(self.species.code)
        super().save(*args, **kwargs)

    @classmethod
    def generate_id_for_species(cls, species_code: str) -> str:
        year = timezone.now().year
        with transaction.atomic():
            GemstoneIDSequence.objects.get_or_create(
                species_code=species_code,
                year=year,
                defaults={"last_sequence": 0},
            )
            sequence = GemstoneIDSequence.objects.select_for_update().get(
                species_code=species_code,
                year=year,
            )
            sequence.last_sequence += 1
            sequence.save(update_fields=["last_sequence"])
            return f"CEY-{species_code}-{year}-{sequence.last_sequence:06d}"

    def transition_to(self, new_state: str) -> None:
        allowed = LIFECYCLE_TRANSITIONS.get(self.lifecycle_state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Cannot transition from '{self.lifecycle_state}' to '{new_state}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )
        self.lifecycle_state = new_state
        self.save(update_fields=["lifecycle_state", "updated_at"])


# ---------------------------------------------------------------------------
# Inventory Item — module 1.4
# ---------------------------------------------------------------------------

class InventorySource(models.TextChoices):
    COMPANY_OWNED = "company_owned", "Company Owned"
    CONSIGNMENT = "consignment", "Consignment"
    SUPPLIER = "supplier", "Supplier"


class CustodyStatus(models.TextChoices):
    IN_HOUSE = "in_house", "In House"
    WITH_GEMOLOGIST = "with_gemologist", "With Gemologist"
    WITH_PHOTOGRAPHER = "with_photographer", "With Photographer"
    WITH_COURIER = "with_courier", "With Courier"
    AT_LABORATORY = "at_laboratory", "At Laboratory"
    DELIVERED_TO_CUSTOMER = "delivered_to_customer", "Delivered to Customer"


class ListingStatus(models.TextChoices):
    UNLISTED = "unlisted", "Unlisted"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    SOLD_OUT = "sold_out", "Sold Out"
    ARCHIVED = "archived", "Archived"


class InventoryItem(models.Model):
    """
    The business/operational record for a physical gemstone.

    PhysicalGemstone = gemological identity and lifecycle.
    InventoryItem    = ownership, location, cost, and listing status.

    One PhysicalGemstone has exactly one InventoryItem.
    This separation allows the gemological record to remain clean
    while the inventory record carries business-specific fields
    that may change over time (price, location, status).

    Designed to support future supplier/consignment ownership
    without requiring a schema change.
    """

    physical_gemstone = models.OneToOneField(
        PhysicalGemstone,
        on_delete=models.PROTECT,
        related_name="inventory_item",
    )

    # Ownership & source
    inventory_source = models.CharField(
        max_length=20,
        choices=InventorySource.choices,
        default=InventorySource.COMPANY_OWNED,
    )
    # Reserved for future supplier support — null means company-owned
    supplier_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="External supplier reference — for future supplier/consignment use",
    )

    # Location & custody
    current_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Physical storage location, e.g. 'Safe A - Drawer 3'",
    )
    custody_status = models.CharField(
        max_length=30,
        choices=CustodyStatus.choices,
        default=CustodyStatus.IN_HOUSE,
    )

    # Cost — internal, never exposed to customers
    acquisition_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Internal acquisition cost in LKR",
    )

    # Certification & listing status
    is_certified = models.BooleanField(default=False)
    listing_status = models.CharField(
        max_length=20,
        choices=ListingStatus.choices,
        default=ListingStatus.UNLISTED,
    )

    # Reservation & sale flags — updated by commerce layer in later modules
    is_reserved = models.BooleanField(default=False)
    is_sold = models.BooleanField(default=False)

    # Export & delivery flags — updated by shipping layer in later modules
    is_export_ready = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ["-created_at"]

    def __str__(self):
        return f"INV — {self.physical_gemstone.gemstone_id}"

    @property
    def gemstone_id(self):
        return self.physical_gemstone.gemstone_id

    @property
    def is_available(self) -> bool:
        """
        A gemstone is available for purchase when it is actively listed,
        not reserved, and not sold.
        """
        return (
            self.listing_status == ListingStatus.ACTIVE
            and not self.is_reserved
            and not self.is_sold
        )


# ---------------------------------------------------------------------------
# Inventory Audit Log — module 1.5
# ---------------------------------------------------------------------------

class AuditEvent(models.TextChoices):
    # PhysicalGemstone lifecycle events
    GEMSTONE_CREATED = "gemstone_created", "Gemstone Created"
    LIFECYCLE_TRANSITION = "lifecycle_transition", "Lifecycle Transition"

    # InventoryItem events
    INVENTORY_CREATED = "inventory_created", "Inventory Item Created"
    LISTING_STATUS_CHANGED = "listing_status_changed", "Listing Status Changed"
    CUSTODY_CHANGED = "custody_changed", "Custody Changed"
    LOCATION_CHANGED = "location_changed", "Location Changed"
    RESERVATION_SET = "reservation_set", "Reservation Set"
    RESERVATION_RELEASED = "reservation_released", "Reservation Released"
    MARKED_SOLD = "marked_sold", "Marked Sold"
    MARKED_EXPORT_READY = "marked_export_ready", "Marked Export Ready"
    MARKED_DELIVERED = "marked_delivered", "Marked Delivered"
    CERTIFICATION_STATUS_CHANGED = "certification_status_changed", "Certification Status Changed"

    # General
    NOTE_ADDED = "note_added", "Note Added"
    ADMIN_OVERRIDE = "admin_override", "Admin Override"


class InventoryAuditLog(models.Model):
    """
    Immutable audit record for every meaningful change to a physical gemstone
    or its inventory item.

    Rules:
    - Records are never updated or deleted.
    - Every lifecycle transition on PhysicalGemstone creates a record.
    - Every status change on InventoryItem creates a record.
    - The actor field records who made the change (user email or system).
    - from_state/to_state capture the before/after for state changes.
    - notes captures any additional context provided at the time of change.
    """

    physical_gemstone = models.ForeignKey(
        PhysicalGemstone,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    event = models.CharField(max_length=40, choices=AuditEvent.choices)
    from_state = models.CharField(max_length=100, blank=True)
    to_state = models.CharField(max_length=100, blank=True)
    # Who made the change — user email or "system" for automated changes
    actor = models.CharField(max_length=200, default="system")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inventory Audit Log"
        verbose_name_plural = "Inventory Audit Logs"
        ordering = ["-created_at"]
        # Audit logs are never modified
        default_permissions = ("view",)

    def __str__(self):
        return (
            f"{self.physical_gemstone.gemstone_id} | "
            f"{self.event} | {self.created_at:%Y-%m-%d %H:%M}"
        )

    def save(self, *args, **kwargs):
        # Prevent updates — audit logs are immutable
        if self.pk:
            raise ValueError("Audit log entries cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")
