from django.contrib import admin
from .models import (
    PhysicalGemstone,
    GemstoneIDSequence,
    InventoryItem,
    InventoryAuditLog,
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
