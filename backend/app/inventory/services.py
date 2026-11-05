"""
Inventory service layer.

All state changes to PhysicalGemstone and InventoryItem should go through
these functions rather than being made directly on the models. This ensures
every meaningful change produces an audit log entry.
"""

from django.db import transaction
from .models import (
    PhysicalGemstone,
    InventoryItem,
    InventoryAuditLog,
    AuditEvent,
    ListingStatus,
    CustodyStatus,
)


def transition_gemstone_lifecycle(
    gemstone: PhysicalGemstone,
    new_state: str,
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Transitions a PhysicalGemstone to a new lifecycle state and records
    an audit log entry.

    Raises ValueError if the transition is not permitted.
    """
    from_state = gemstone.lifecycle_state

    with transaction.atomic():
        gemstone.transition_to(new_state)
        log = InventoryAuditLog.objects.create(
            physical_gemstone=gemstone,
            event=AuditEvent.LIFECYCLE_TRANSITION,
            from_state=from_state,
            to_state=new_state,
            actor=actor,
            notes=notes,
        )
    return log


def change_listing_status(
    inventory_item: InventoryItem,
    new_status: str,
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Changes the listing status of an InventoryItem and records an audit log.
    """
    from_status = inventory_item.listing_status

    with transaction.atomic():
        inventory_item.listing_status = new_status
        inventory_item.save(update_fields=["listing_status", "updated_at"])
        log = InventoryAuditLog.objects.create(
            physical_gemstone=inventory_item.physical_gemstone,
            event=AuditEvent.LISTING_STATUS_CHANGED,
            from_state=from_status,
            to_state=new_status,
            actor=actor,
            notes=notes,
        )
    return log


def change_custody(
    inventory_item: InventoryItem,
    new_custody: str,
    new_location: str = "",
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Changes the custody status and optionally the location of an InventoryItem.
    Records a single audit log entry covering both changes.
    """
    from_custody = inventory_item.custody_status

    with transaction.atomic():
        inventory_item.custody_status = new_custody
        if new_location:
            inventory_item.current_location = new_location
        inventory_item.save(update_fields=["custody_status", "current_location", "updated_at"])
        log = InventoryAuditLog.objects.create(
            physical_gemstone=inventory_item.physical_gemstone,
            event=AuditEvent.CUSTODY_CHANGED,
            from_state=from_custody,
            to_state=new_custody,
            actor=actor,
            notes=notes or (f"Location: {new_location}" if new_location else ""),
        )
    return log


def set_reservation(
    inventory_item: InventoryItem,
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Marks an InventoryItem as reserved.
    Raises ValueError if the item is not available.
    """
    if not inventory_item.is_available:
        raise ValueError(
            f"Cannot reserve gemstone {inventory_item.gemstone_id} — "
            f"it is not available (listing_status={inventory_item.listing_status}, "
            f"is_reserved={inventory_item.is_reserved}, is_sold={inventory_item.is_sold})."
        )

    with transaction.atomic():
        inventory_item.is_reserved = True
        inventory_item.save(update_fields=["is_reserved", "updated_at"])
        log = InventoryAuditLog.objects.create(
            physical_gemstone=inventory_item.physical_gemstone,
            event=AuditEvent.RESERVATION_SET,
            from_state="available",
            to_state="reserved",
            actor=actor,
            notes=notes,
        )
    return log


def release_reservation(
    inventory_item: InventoryItem,
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Releases a reservation on an InventoryItem.
    Raises ValueError if the item is not currently reserved.
    """
    if not inventory_item.is_reserved:
        raise ValueError(
            f"Cannot release reservation on {inventory_item.gemstone_id} — "
            f"it is not currently reserved."
        )

    with transaction.atomic():
        inventory_item.is_reserved = False
        inventory_item.save(update_fields=["is_reserved", "updated_at"])
        log = InventoryAuditLog.objects.create(
            physical_gemstone=inventory_item.physical_gemstone,
            event=AuditEvent.RESERVATION_RELEASED,
            from_state="reserved",
            to_state="available",
            actor=actor,
            notes=notes,
        )
    return log


def mark_sold(
    inventory_item: InventoryItem,
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Marks an InventoryItem as sold and updates the gemstone lifecycle state.
    Raises ValueError if the item is already sold.
    """
    if inventory_item.is_sold:
        raise ValueError(
            f"Gemstone {inventory_item.gemstone_id} is already marked as sold."
        )

    with transaction.atomic():
        inventory_item.is_reserved = False
        inventory_item.is_sold = True
        inventory_item.listing_status = ListingStatus.SOLD_OUT
        inventory_item.save(update_fields=[
            "is_reserved", "is_sold", "listing_status", "updated_at"
        ])
        log = InventoryAuditLog.objects.create(
            physical_gemstone=inventory_item.physical_gemstone,
            event=AuditEvent.MARKED_SOLD,
            from_state="available",
            to_state="sold",
            actor=actor,
            notes=notes,
        )
    return log


def mark_export_ready(
    inventory_item: InventoryItem,
    actor: str = "system",
    notes: str = "",
) -> InventoryAuditLog:
    """
    Marks an InventoryItem as export-ready.
    Raises ValueError if the item is not sold.
    """
    if not inventory_item.is_sold:
        raise ValueError(
            f"Gemstone {inventory_item.gemstone_id} must be sold before marking export-ready."
        )

    with transaction.atomic():
        inventory_item.is_export_ready = True
        inventory_item.save(update_fields=["is_export_ready", "updated_at"])
        log = InventoryAuditLog.objects.create(
            physical_gemstone=inventory_item.physical_gemstone,
            event=AuditEvent.MARKED_EXPORT_READY,
            from_state="sold",
            to_state="export_ready",
            actor=actor,
            notes=notes,
        )
    return log
