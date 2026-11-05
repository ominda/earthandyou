from django.contrib import admin
from .models import Cart, CartItem, Reservation, CheckoutSession


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["product", "added_at"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["customer", "item_count", "created_at", "updated_at"]
    search_fields = ["customer__email"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CartItemInline]

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = "Items"


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["customer", "product", "status", "expires_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["customer__email", "product__inventory_item__physical_gemstone__gemstone_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ["customer", "reservation", "status", "total_usd", "expires_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["customer__email"]
    readonly_fields = ["shipping_address", "billing_address", "subtotal_usd", "shipping_usd", "total_usd", "created_at", "updated_at"]
