from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.utils.html import format_html
from .models import (
    Cart, CartItem, Reservation, CheckoutSession,
    Order, OrderStatusLog, Payment, Refund,
    Shipment, ExportRecord, ShippingRate,
)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Reservation & Checkout
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    extra = 0
    fields = ["from_status", "to_status", "actor", "notes", "created_at"]
    readonly_fields = ["from_status", "to_status", "actor", "notes", "created_at"]
    ordering = ["created_at"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ["provider", "provider_reference", "amount_usd", "status", "created_at"]
    readonly_fields = ["provider", "provider_reference", "amount_usd", "status", "created_at"]

    def has_add_permission(self, request, obj=None):
        return False


def _transition_order(new_status, description):
    def action(modeladmin, request, queryset):
        for order in queryset:
            old = order.status
            if old == new_status:
                continue
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])
            OrderStatusLog.objects.create(
                order=order,
                from_status=old,
                to_status=new_status,
                actor=request.user.email,
            )
    action.__name__ = f"mark_{new_status}"
    action.short_description = description
    return action


mark_confirmed = _transition_order(Order.Status.CONFIRMED, "Mark selected orders → Confirmed")
mark_processing = _transition_order(Order.Status.PROCESSING, "Mark selected orders → Processing")
mark_cancelled = _transition_order(Order.Status.CANCELLED, "Mark selected orders → Cancelled")
mark_refunded = _transition_order(Order.Status.REFUNDED, "Mark selected orders → Refunded")


def _mark_shipped(modeladmin, request, queryset):
    ok = skipped = 0
    for order in queryset:
        if order.status == Order.Status.SHIPPED:
            skipped += 1
            continue
        with transaction.atomic():
            old = order.status
            order.status = Order.Status.SHIPPED
            order.save(update_fields=["status", "updated_at"])
            OrderStatusLog.objects.create(
                order=order, from_status=old,
                to_status=Order.Status.SHIPPED, actor=request.user.email,
            )
            try:
                shipment = order.shipment
                if shipment.status not in (Shipment.Status.DISPATCHED, Shipment.Status.IN_TRANSIT):
                    shipment.status = Shipment.Status.DISPATCHED
                    shipment.save(update_fields=["status", "updated_at"])
            except Shipment.DoesNotExist:
                pass
        ok += 1
    if ok:
        modeladmin.message_user(request, f"{ok} order(s) marked Shipped.")
    if skipped:
        modeladmin.message_user(request, f"{skipped} order(s) already Shipped.", level=messages.WARNING)

_mark_shipped.short_description = "Mark selected orders → Shipped"


def _mark_delivered(modeladmin, request, queryset):
    ok = skipped = 0
    for order in queryset:
        if order.status == Order.Status.DELIVERED:
            skipped += 1
            continue
        with transaction.atomic():
            old = order.status
            order.status = Order.Status.DELIVERED
            order.save(update_fields=["status", "updated_at"])
            OrderStatusLog.objects.create(
                order=order, from_status=old,
                to_status=Order.Status.DELIVERED, actor=request.user.email,
            )
            try:
                shipment = order.shipment
                if shipment.status != Shipment.Status.DELIVERED:
                    shipment.status = Shipment.Status.DELIVERED
                    shipment.save(update_fields=["status", "updated_at"])
            except Shipment.DoesNotExist:
                pass
        ok += 1
    if ok:
        modeladmin.message_user(request, f"{ok} order(s) marked Delivered.")
    if skipped:
        modeladmin.message_user(request, f"{skipped} order(s) already Delivered.", level=messages.WARNING)

_mark_delivered.short_description = "Mark selected orders → Delivered"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_ref", "customer", "gemstone_id", "status",
        "total_usd", "payment_reference", "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["order_ref", "customer__email", "gemstone_id", "payment_reference"]
    readonly_fields = [
        "order_ref", "customer", "checkout_session",
        "gemstone_id", "product_headline", "product_slug",
        "subtotal_usd", "shipping_usd", "total_usd",
        "shipping_address", "billing_address",
        "created_at", "updated_at",
    ]
    inlines = [OrderStatusLogInline, PaymentInline]
    actions = [mark_confirmed, mark_processing, _mark_shipped, _mark_delivered, mark_cancelled, mark_refunded]
    fieldsets = [
        ("Reference", {
            "fields": ["order_ref", "customer", "checkout_session"],
        }),
        ("Product Snapshot", {
            "fields": ["gemstone_id", "product_headline", "product_slug"],
        }),
        ("Pricing", {
            "fields": ["subtotal_usd", "shipping_usd", "total_usd"],
        }),
        ("Addresses", {
            "fields": ["shipping_address", "billing_address"],
            "classes": ["collapse"],
        }),
        ("Status & Payment", {
            "fields": ["status", "payment_reference", "notes"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "provider", "provider_reference", "amount_usd", "status", "created_at"]
    list_filter = ["status", "provider"]
    search_fields = ["order__order_ref", "provider_reference"]
    readonly_fields = ["order", "provider", "provider_reference", "amount_usd", "raw_response", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

def _refund_action(new_status, description):
    def action(modeladmin, request, queryset):
        count = queryset.exclude(status=new_status).update(status=new_status)
        modeladmin.message_user(request, f"{count} refund(s) set to {new_status}.")
    action.__name__ = f"refund_{new_status}"
    action.short_description = description
    return action


refund_succeeded = _refund_action(Refund.Status.SUCCEEDED, "Refund → Succeeded")
refund_failed = _refund_action(Refund.Status.FAILED, "Refund → Failed")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["order", "amount_usd", "status", "requested_by", "provider_reference", "created_at"]
    list_filter = ["status"]
    search_fields = ["order__order_ref", "provider_reference", "requested_by"]
    readonly_fields = ["order", "payment", "amount_usd", "raw_response", "created_at", "updated_at"]
    actions = [refund_succeeded, refund_failed]
    fieldsets = [
        ("Order & Payment", {
            "fields": ["order", "payment", "amount_usd"],
        }),
        ("Refund Details", {
            "fields": ["reason", "status", "provider_reference", "requested_by"],
        }),
        ("Provider Response", {
            "fields": ["raw_response"],
            "classes": ["collapse"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# ---------------------------------------------------------------------------
# Shipment
# ---------------------------------------------------------------------------

def _shipment_action(new_status, description):
    def action(modeladmin, request, queryset):
        updated = queryset.exclude(status=new_status)
        count = updated.update(status=new_status)
        modeladmin.message_user(request, f"{count} shipment(s) set to {new_status}.")
    action.__name__ = f"shipment_{new_status}"
    action.short_description = description
    return action


shipment_dispatched = _shipment_action(Shipment.Status.DISPATCHED, "Shipment → Dispatched")
shipment_in_transit = _shipment_action(Shipment.Status.IN_TRANSIT, "Shipment → In Transit")
shipment_delivered = _shipment_action(Shipment.Status.DELIVERED, "Shipment → Delivered")
shipment_returned = _shipment_action(Shipment.Status.RETURNED, "Shipment → Returned")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "order", "carrier", "tracking_number", "status",
        "estimated_delivery_date", "actual_delivery_date",
    ]
    list_filter = ["status", "carrier"]
    search_fields = ["order__order_ref", "carrier", "tracking_number"]
    actions = [shipment_dispatched, shipment_in_transit, shipment_delivered, shipment_returned]
    fieldsets = [
        ("Order", {
            "fields": ["order"],
        }),
        ("Carrier", {
            "fields": ["carrier", "tracking_number", "tracking_url_link"],
        }),
        ("Status & Dates", {
            "fields": ["status", "estimated_delivery_date", "actual_delivery_date"],
        }),
        ("Notes", {
            "fields": ["notes"],
            "classes": ["collapse"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
    readonly_fields = ["tracking_url_link", "created_at", "updated_at"]

    def tracking_url_link(self, obj):
        if obj.tracking_url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.tracking_url, obj.tracking_url)
        return "—"
    tracking_url_link.short_description = "Tracking URL"


# ---------------------------------------------------------------------------
# Export Record
# ---------------------------------------------------------------------------

def _compliance_action(new_status, description):
    def action(modeladmin, request, queryset):
        count = queryset.exclude(compliance_status=new_status).update(compliance_status=new_status)
        modeladmin.message_user(request, f"{count} export record(s) set to {new_status}.")
    action.__name__ = f"compliance_{new_status}"
    action.short_description = description
    return action


compliance_cleared = _compliance_action(ExportRecord.ComplianceStatus.CLEARED, "Compliance → Cleared")
compliance_rejected = _compliance_action(ExportRecord.ComplianceStatus.REJECTED, "Compliance → Rejected")


@admin.register(ExportRecord)
class ExportRecordAdmin(admin.ModelAdmin):
    list_display = [
        "order", "destination_country", "declared_value_usd",
        "compliance_status", "export_permit_number", "created_at",
    ]
    list_filter = ["compliance_status", "destination_country"]
    search_fields = ["order__order_ref", "export_permit_number", "customs_declaration_number"]
    readonly_fields = ["created_at", "updated_at"]
    actions = [compliance_cleared, compliance_rejected]
    fieldsets = [
        ("Order", {
            "fields": ["order"],
        }),
        ("Export Details", {
            "fields": [
                "destination_country", "declared_value_usd",
                "export_permit_number", "customs_declaration_number",
            ],
        }),
        ("Compliance", {
            "fields": ["compliance_status", "notes"],
        }),
        ("Documents", {
            "fields": ["document_s3_keys"],
            "classes": ["collapse"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# ---------------------------------------------------------------------------
# Shipping Rate
# ---------------------------------------------------------------------------

@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ["value_tier", "rate_usd", "updated_at"]
    readonly_fields = ["updated_at"]
