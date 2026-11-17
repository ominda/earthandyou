from django.contrib import admin
from django.contrib import messages
from .models import (
    PhysicalGemstone,
    GemstoneIDSequence,
    GemstoneLifecycleState,
    InventoryItem,
    InventoryAuditLog,
    AuditEvent,
    ListingStatus,
)


class InventoryItemInline(admin.StackedInline):
    model = InventoryItem
    extra = 0
    fields = [
        "inventory_source", "current_location", "custody_status",
        "acquisition_cost", "is_certified", "listing_status",
        "is_reserved", "is_sold", "is_export_ready", "is_delivered",
        "supplier_reference",
    ]
    readonly_fields = ["created_at", "updated_at"]


class InventoryAuditLogInline(admin.TabularInline):
    model = InventoryAuditLog
    extra = 0
    fields = ["event", "from_state", "to_state", "actor", "notes", "created_at"]
    readonly_fields = ["event", "from_state", "to_state", "actor", "notes", "created_at"]
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def _lifecycle_action(new_state, description):
    def action(modeladmin, request, queryset):
        ok = skipped = 0
        for gem in queryset:
            old = gem.lifecycle_state
            try:
                gem.transition_to(new_state)
                InventoryAuditLog.objects.create(
                    physical_gemstone=gem,
                    event=AuditEvent.LIFECYCLE_TRANSITION,
                    from_state=old,
                    to_state=new_state,
                    actor=request.user.email,
                )
                ok += 1
            except ValueError:
                skipped += 1
        if ok:
            modeladmin.message_user(request, f"{ok} gemstone(s) transitioned to {new_state}.")
        if skipped:
            modeladmin.message_user(
                request,
                f"{skipped} gemstone(s) skipped — invalid transition to {new_state}.",
                level=messages.WARNING,
            )
    action.__name__ = f"transition_to_{new_state}"
    action.short_description = description
    return action


transition_to_tested = _lifecycle_action(GemstoneLifecycleState.TESTED, "Lifecycle → Tested")
transition_to_certified = _lifecycle_action(GemstoneLifecycleState.CERTIFIED, "Lifecycle → Certified")
transition_to_photographed = _lifecycle_action(GemstoneLifecycleState.PHOTOGRAPHED, "Lifecycle → Photographed")
transition_to_stored = _lifecycle_action(GemstoneLifecycleState.STORED, "Lifecycle → Stored")
transition_to_listed = _lifecycle_action(GemstoneLifecycleState.LISTED, "Lifecycle → Listed")


@admin.register(PhysicalGemstone)
class PhysicalGemstoneAdmin(admin.ModelAdmin):
    list_display = [
        "gemstone_id", "species", "variety", "lifecycle_state",
        "acquisition_date", "inventory_status", "created_at",
    ]
    list_filter = ["lifecycle_state", "species", "acquisition_date"]
    search_fields = ["gemstone_id", "species__name", "variety__name"]
    readonly_fields = ["gemstone_id", "created_at", "updated_at"]
    inlines = [InventoryItemInline, InventoryAuditLogInline]
    actions = [
        transition_to_tested, transition_to_certified,
        transition_to_photographed, transition_to_stored, transition_to_listed,
    ]
    fieldsets = [
        ("Identity", {
            "fields": ["gemstone_id", "species", "variety"],
        }),
        ("Lifecycle", {
            "fields": ["lifecycle_state"],
        }),
        ("Acquisition", {
            "fields": ["acquisition_date", "acquisition_notes"],
        }),
        ("Internal", {
            "fields": ["internal_notes"],
            "classes": ["collapse"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def inventory_status(self, obj):
        try:
            return obj.inventory_item.listing_status
        except InventoryItem.DoesNotExist:
            return "—"
    inventory_status.short_description = "Listing Status"


def _listing_action(new_status, description):
    def action(modeladmin, request, queryset):
        updated = queryset.exclude(listing_status=new_status)
        for item in updated:
            old = item.listing_status
            item.listing_status = new_status
            item.save(update_fields=["listing_status", "updated_at"])
            InventoryAuditLog.objects.create(
                physical_gemstone=item.physical_gemstone,
                event=AuditEvent.LISTING_STATUS_CHANGED,
                from_state=old,
                to_state=new_status,
                actor=request.user.email,
            )
        modeladmin.message_user(request, f"{updated.count()} item(s) set to {new_status}.")
    action.__name__ = f"set_listing_{new_status}"
    action.short_description = description
    return action


set_listing_active = _listing_action(ListingStatus.ACTIVE, "Listing → Active")
set_listing_paused = _listing_action(ListingStatus.PAUSED, "Listing → Paused")
set_listing_archived = _listing_action(ListingStatus.ARCHIVED, "Listing → Archived")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        "gemstone_id", "inventory_source", "listing_status",
        "custody_status", "is_reserved", "is_sold", "is_available",
        "current_location",
    ]
    list_filter = [
        "listing_status", "inventory_source", "custody_status",
        "is_reserved", "is_sold", "is_certified",
    ]
    search_fields = ["physical_gemstone__gemstone_id"]
    readonly_fields = ["created_at", "updated_at"]
    actions = [set_listing_active, set_listing_paused, set_listing_archived]
    fieldsets = [
        ("Gemstone", {
            "fields": ["physical_gemstone"],
        }),
        ("Ownership & Source", {
            "fields": ["inventory_source", "supplier_reference"],
        }),
        ("Location & Custody", {
            "fields": ["current_location", "custody_status"],
        }),
        ("Cost", {
            "fields": ["acquisition_cost"],
            "classes": ["collapse"],
        }),
        ("Status", {
            "fields": [
                "is_certified", "listing_status",
                "is_reserved", "is_sold",
                "is_export_ready", "is_delivered",
            ],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def gemstone_id(self, obj):
        return obj.physical_gemstone.gemstone_id
    gemstone_id.short_description = "Gemstone ID"

    def is_available(self, obj):
        return obj.is_available
    is_available.boolean = True
    is_available.short_description = "Available"


@admin.register(InventoryAuditLog)
class InventoryAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "physical_gemstone", "event", "from_state",
        "to_state", "actor", "created_at",
    ]
    list_filter = ["event", "actor"]
    search_fields = ["physical_gemstone__gemstone_id", "actor", "notes"]
    readonly_fields = [
        "physical_gemstone", "event", "from_state",
        "to_state", "actor", "notes", "created_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GemstoneIDSequence)
class GemstoneIDSequenceAdmin(admin.ModelAdmin):
    list_display = ["species_code", "year", "last_sequence"]
    readonly_fields = ["species_code", "year", "last_sequence"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
