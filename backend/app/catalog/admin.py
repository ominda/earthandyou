from django.contrib import admin
from .models import (
    GemstoneSpecies,
    GemstoneVariety,
    GemstoneAttributeDefinition,
    GemstoneAttributeOption,
    Product,
    ProductMedia,
)


class GemstoneVarietyInline(admin.TabularInline):
    model = GemstoneVariety
    extra = 0
    fields = ["name", "code", "typical_colors", "is_active"]


class GemstoneAttributeDefinitionInline(admin.TabularInline):
    model = GemstoneAttributeDefinition
    extra = 0
    fields = ["name", "key", "data_type", "unit", "is_required", "is_filterable", "is_displayed", "display_order"]


@admin.register(GemstoneSpecies)
class GemstoneSpeciesAdmin(admin.ModelAdmin):
    list_display = ["name", "common_name", "code", "is_active", "variety_count", "attribute_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "common_name", "code"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [GemstoneVarietyInline, GemstoneAttributeDefinitionInline]

    def variety_count(self, obj):
        return obj.varieties.count()
    variety_count.short_description = "Varieties"

    def attribute_count(self, obj):
        return obj.attribute_definitions.count()
    attribute_count.short_description = "Attributes"


@admin.register(GemstoneVariety)
class GemstoneVarietyAdmin(admin.ModelAdmin):
    list_display = ["name", "species", "code", "typical_colors", "is_active"]
    list_filter = ["is_active", "species"]
    search_fields = ["name", "code", "species__name"]
    readonly_fields = ["created_at", "updated_at"]


class GemstoneAttributeOptionInline(admin.TabularInline):
    model = GemstoneAttributeOption
    extra = 0
    fields = ["value", "display_order"]


@admin.register(GemstoneAttributeDefinition)
class GemstoneAttributeDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "species", "key", "data_type", "is_required", "is_filterable", "is_displayed", "display_order"]
    list_filter = ["species", "data_type", "is_required", "is_filterable"]
    search_fields = ["name", "key", "species__name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [GemstoneAttributeOptionInline]


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 0
    fields = ["media_type", "s3_key", "alt_text", "display_order", "is_primary"]
    ordering = ["display_order"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["gemstone_id", "price_usd", "value_tier", "listing_status", "is_available", "created_at"]
    list_filter = ["value_tier", "listing_status"]
    search_fields = ["inventory_item__physical_gemstone__gemstone_id", "headline", "slug"]
    readonly_fields = ["slug", "created_at", "updated_at"]
    inlines = [ProductMediaInline]
    fieldsets = [
        (None, {"fields": ["inventory_item", "listing_status", "value_tier"]}),
        ("Pricing", {"fields": ["price_usd"]}),
        ("Content", {"fields": ["headline", "description"]}),
        ("SEO", {"fields": ["slug", "meta_title", "meta_description"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]

    def gemstone_id(self, obj):
        return obj.gemstone_id
    gemstone_id.short_description = "Gemstone ID"

    def is_available(self, obj):
        return obj.is_available
    is_available.boolean = True
    is_available.short_description = "Available"
