from django.conf import settings
from django.db import models
from django.utils import timezone


class Cart(models.Model):
    """
    One cart per customer. Created on first add-to-cart.
    Items are cleared on order placement (Phase 4.4).
    """

    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart — {self.customer.email}"


class CartItem(models.Model):
    """
    A single product in a cart.

    No quantity field — every product is a unique physical gemstone.
    Duplicate products in the same cart are prevented by the unique constraint.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart")
        ]
        ordering = ["added_at"]

    def __str__(self):
        return f"{self.cart.customer.email} — {self.product.gemstone_id}"


class Reservation(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        RELEASED = "released", "Released"
        CONVERTED = "converted", "Converted"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"
        ordering = ["-created_at"]
        constraints = [
            # Only one active reservation per product at a time
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(status="active"),
                name="unique_active_reservation_per_product",
            )
        ]

    def __str__(self):
        return f"{self.customer.email} — {self.product.gemstone_id} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE and timezone.now() < self.expires_at


class CheckoutSession(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"
        EXPIRED = "expired", "Expired"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checkout_sessions",
    )
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.PROTECT,
        related_name="checkout_session",
    )
    # Address snapshots — stored as JSON so changes to saved addresses
    # don't affect in-flight or completed checkouts
    shipping_address = models.JSONField()
    billing_address = models.JSONField()

    subtotal_usd = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_usd = models.DecimalField(max_digits=12, decimal_places=2)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Checkout Session"
        verbose_name_plural = "Checkout Sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.email} — {self.reservation.product.gemstone_id} ({self.status})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.PENDING and timezone.now() < self.expires_at


class Order(models.Model):
    """
    Immutable record of a completed purchase.

    Created atomically when a customer confirms checkout.
    All pricing and address data is snapshotted at creation time —
    subsequent changes to products or addresses do not affect the order.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    # Human-readable order reference, e.g. ORD-2026-000001
    order_ref = models.CharField(max_length=30, unique=True, editable=False)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    checkout_session = models.OneToOneField(
        CheckoutSession,
        on_delete=models.PROTECT,
        related_name="order",
    )

    # Product snapshot — so order history survives product edits
    gemstone_id = models.CharField(max_length=30)
    product_headline = models.CharField(max_length=200, blank=True)
    product_slug = models.SlugField(max_length=60)

    # Pricing snapshot
    subtotal_usd = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_usd = models.DecimalField(max_digits=12, decimal_places=2)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2)

    # Address snapshots (copied from CheckoutSession)
    shipping_address = models.JSONField()
    billing_address = models.JSONField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )

    # Populated by the payment layer (Phase 4.5+)
    payment_reference = models.CharField(max_length=200, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_ref} — {self.customer.email} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.order_ref:
            self.order_ref = self._generate_order_ref()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_ref() -> str:
        from django.utils import timezone as tz
        year = tz.now().year
        # Use DB sequence via a simple count — good enough for low-volume luxury sales
        count = Order.objects.filter(created_at__year=year).count() + 1
        return f"ORD-{year}-{count:06d}"


class Payment(models.Model):
    """
    A single payment attempt against an Order.

    One Order may have multiple Payment records (e.g. first attempt failed,
    customer retried). Only one Payment per Order should ever reach
    status=succeeded.

    raw_response stores the full provider payload for audit/debugging.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=50, help_text="e.g. 'webxpay', 'stripe'")
    provider_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="Transaction ID or reference returned by the provider",
    )
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_ref} | {self.provider} | {self.status}"


class OrderStatusLog(models.Model):
    """
    Append-only log of every status transition on an Order.
    """

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="status_logs")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    actor = models.CharField(max_length=200, default="system")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order Status Log"
        verbose_name_plural = "Order Status Logs"
        ordering = ["created_at"]
        default_permissions = ("view",)

    def __str__(self):
        return f"{self.order.order_ref} | {self.from_status} → {self.to_status}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Order status log entries cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Order status log entries cannot be deleted.")


class ShippingRate(models.Model):
    """
    Configurable shipping rate per value tier.

    One row per ValueTier. Staff update these via the admin API;
    the checkout service reads from here, falling back to hardcoded
    defaults if no record exists for a given tier.
    """

    from catalog.models import ValueTier as _VT

    value_tier = models.CharField(
        max_length=20,
        choices=_VT.choices,
        unique=True,
    )
    rate_usd = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shipping Rate"
        verbose_name_plural = "Shipping Rates"
        ordering = ["value_tier"]

    def __str__(self):
        return f"{self.value_tier} — ${self.rate_usd}"


class Shipment(models.Model):
    """
    Tracks the physical dispatch of an order.

    One Order has at most one Shipment. Created by staff when the order
    is packed and handed to a carrier. Status transitions drive the
    order status forward (processing → shipped → delivered).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DISPATCHED = "dispatched", "Dispatched"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        RETURNED = "returned", "Returned"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="shipment")
    carrier = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=200, blank=True)
    tracking_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shipment"
        verbose_name_plural = "Shipments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_ref} | {self.carrier} | {self.status}"


class ExportRecord(models.Model):
    """
    Export documentation and compliance record for an order.

    Created by staff when an order is being prepared for international dispatch.
    Tracks export permit, customs declaration, declared value, and compliance
    clearance status. Document S3 keys reference uploaded export paperwork.
    """

    class ComplianceStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CLEARED = "cleared", "Cleared"
        REJECTED = "rejected", "Rejected"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="export_record")
    export_permit_number = models.CharField(max_length=100, blank=True)
    customs_declaration_number = models.CharField(max_length=100, blank=True)
    declared_value_usd = models.DecimalField(max_digits=12, decimal_places=2)
    destination_country = models.CharField(max_length=100)
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.PENDING,
    )
    # Newline-separated S3 keys for export documents (permits, declarations, etc.)
    document_s3_keys = models.TextField(
        blank=True,
        help_text="S3 object keys for export documents, one per line",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Export Record"
        verbose_name_plural = "Export Records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_ref} | export | {self.compliance_status}"

    @property
    def documents(self) -> list:
        if not self.document_s3_keys:
            return []
        return [k.strip() for k in self.document_s3_keys.splitlines() if k.strip()]


class Refund(models.Model):
    """
    A refund request against a succeeded Payment.

    One Order may have at most one Refund — partial refunds are not
    supported for unique physical gemstones.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="refund")
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider_reference = models.CharField(max_length=200, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    requested_by = models.CharField(max_length=200, default="system")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_ref} | refund | {self.status}"
