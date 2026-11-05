from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from catalog.models import Product, ValueTier
from .models import Cart, CartItem, Reservation, CheckoutSession, Order, OrderStatusLog, Payment, Refund, ShippingRate, Shipment, ExportRecord


def _notify(module_name: str, fn_name: str, *args) -> None:
    """Call an outbox notification function, swallowing all errors."""
    try:
        import importlib
        mod = importlib.import_module(f"outbox.{module_name}")
        getattr(mod, fn_name)(*args)
    except Exception:
        pass


class CartError(Exception):
    pass


def get_or_create_cart(customer) -> Cart:
    cart, _ = Cart.objects.get_or_create(customer=customer)
    return cart


def add_to_cart(customer, product_id: int) -> CartItem:
    try:
        product = Product.objects.select_related("inventory_item").get(pk=product_id)
    except Product.DoesNotExist:
        raise CartError("Product not found.")

    if not product.is_available:
        raise CartError("This product is not available.")

    cart = get_or_create_cart(customer)

    try:
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    except IntegrityError:
        raise CartError("Product is already in your cart.")

    if not created:
        raise CartError("Product is already in your cart.")

    return item


def remove_from_cart(customer, product_id: int) -> None:
    try:
        cart = customer.cart
    except Cart.DoesNotExist:
        raise CartError("Cart not found.")

    deleted, _ = CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    if not deleted:
        raise CartError("Item not found in cart.")


def clear_cart(customer) -> None:
    try:
        customer.cart.items.all().delete()
    except Cart.DoesNotExist:
        pass


def create_reservation(customer, product_id: int) -> Reservation:
    from inventory.services import set_reservation as inventory_set_reservation

    try:
        product = Product.objects.select_related("inventory_item").get(pk=product_id)
    except Product.DoesNotExist:
        raise CartError("Product not found.")

    if not product.is_available:
        raise CartError("This product is not available for reservation.")

    expiry_minutes = getattr(settings, "RESERVATION_EXPIRY_MINUTES", 15)

    with transaction.atomic():
        try:
            inventory_set_reservation(
                product.inventory_item,
                actor=customer.email,
                notes=f"Reserved via checkout by {customer.email}",
            )
        except ValueError as e:
            raise CartError(str(e))

        try:
            reservation = Reservation.objects.create(
                customer=customer,
                product=product,
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            )
        except IntegrityError:
            raise CartError("This product is already reserved.")

        # Remove from cart if present
        CartItem.objects.filter(cart__customer=customer, product=product).delete()

    _notify("reservation_notifications", "notify_reservation_created", reservation)
    return reservation


def release_reservation(reservation: Reservation, actor: str = "system") -> None:
    from inventory.services import release_reservation as inventory_release_reservation

    if reservation.status != Reservation.Status.ACTIVE:
        raise CartError(f"Reservation is already {reservation.status}.")

    with transaction.atomic():
        try:
            inventory_release_reservation(
                reservation.product.inventory_item,
                actor=actor,
                notes=f"Reservation released for {reservation.product.gemstone_id}",
            )
        except ValueError as e:
            raise CartError(str(e))

        reservation.status = Reservation.Status.RELEASED
        reservation.save(update_fields=["status", "updated_at"])


def expire_stale_reservations() -> int:
    """Mark all past-due active reservations as expired and release inventory.
    Returns the number of reservations expired."""
    from inventory.services import release_reservation as inventory_release_reservation

    stale = Reservation.objects.filter(
        status=Reservation.Status.ACTIVE,
        expires_at__lt=timezone.now(),
    ).select_related("product__inventory_item")

    count = 0
    for reservation in stale:
        with transaction.atomic():
            try:
                inventory_release_reservation(
                    reservation.product.inventory_item,
                    actor="system",
                    notes="Reservation expired automatically",
                )
            except ValueError:
                pass  # inventory may already be released
            reservation.status = Reservation.Status.EXPIRED
            reservation.save(update_fields=["status", "updated_at"])
            _notify("reservation_notifications", "notify_reservation_expired", reservation)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Shipping rate helper
# ---------------------------------------------------------------------------

# Default rates by value tier in USD. Override via SHIPPING_RATES setting.
_DEFAULT_SHIPPING_RATES = {
    ValueTier.STANDARD: Decimal("25.00"),
    ValueTier.PREMIUM: Decimal("35.00"),
    ValueTier.LUXURY: Decimal("50.00"),
    ValueTier.ULTRA_LUXURY: Decimal("75.00"),
}


def get_shipping_cost(value_tier: str) -> Decimal:
    try:
        return ShippingRate.objects.get(value_tier=value_tier).rate_usd
    except ShippingRate.DoesNotExist:
        pass
    rates = getattr(settings, "SHIPPING_RATES", _DEFAULT_SHIPPING_RATES)
    return Decimal(str(rates.get(value_tier, _DEFAULT_SHIPPING_RATES[ValueTier.STANDARD])))


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

def _snapshot_address(address) -> dict:
    return {
        "id": address.pk,
        "recipient_name": address.recipient_name,
        "phone": address.phone,
        "line1": address.line1,
        "line2": address.line2,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
    }


def create_checkout_session(
    customer,
    reservation_id: int,
    shipping_address_id: int,
    billing_address_id: int | None = None,
) -> CheckoutSession:
    from customers.models import CustomerAddress

    # Validate reservation
    try:
        reservation = Reservation.objects.select_related(
            "product__inventory_item"
        ).get(pk=reservation_id, customer=customer)
    except Reservation.DoesNotExist:
        raise CartError("Reservation not found.")

    if not reservation.is_active:
        raise CartError("Reservation has expired or is no longer active.")

    # Guard against duplicate checkout sessions
    if CheckoutSession.objects.filter(
        reservation=reservation,
        status=CheckoutSession.Status.PENDING,
    ).exists():
        raise CartError("A checkout session already exists for this reservation.")

    # Validate shipping address
    try:
        shipping_addr = CustomerAddress.objects.get(
            pk=shipping_address_id, customer=customer
        )
    except CustomerAddress.DoesNotExist:
        raise CartError("Shipping address not found.")

    # Billing address — falls back to shipping address if not provided
    if billing_address_id:
        try:
            billing_addr = CustomerAddress.objects.get(
                pk=billing_address_id, customer=customer
            )
        except CustomerAddress.DoesNotExist:
            raise CartError("Billing address not found.")
    else:
        billing_addr = shipping_addr

    product = reservation.product
    subtotal = product.price_usd
    shipping = get_shipping_cost(product.value_tier)
    total = subtotal + shipping

    session = CheckoutSession.objects.create(
        customer=customer,
        reservation=reservation,
        shipping_address=_snapshot_address(shipping_addr),
        billing_address=_snapshot_address(billing_addr),
        subtotal_usd=subtotal,
        shipping_usd=shipping,
        total_usd=total,
        expires_at=reservation.expires_at,
    )
    return session


# ---------------------------------------------------------------------------
# Order placement
# ---------------------------------------------------------------------------

def place_order(customer, checkout_session_id: int) -> Order:
    """Convert a pending CheckoutSession into an Order.

    Atomically:
    - Validates the session is still active and belongs to the customer
    - Guards against duplicate orders
    - Marks inventory as sold (via inventory service)
    - Marks the reservation as converted
    - Marks the checkout session as completed
    - Creates the Order and an initial OrderStatusLog entry
    """
    from inventory.services import mark_sold as inventory_mark_sold

    try:
        session = CheckoutSession.objects.select_related(
            "reservation__product__inventory_item"
        ).get(pk=checkout_session_id, customer=customer)
    except CheckoutSession.DoesNotExist:
        raise CartError("Checkout session not found.")

    if not session.is_active:
        raise CartError("Checkout session has expired or is no longer active.")

    # Guard against duplicate orders
    if Order.objects.filter(checkout_session=session).exists():
        raise CartError("An order already exists for this checkout session.")

    product = session.reservation.product

    with transaction.atomic():
        # Mark inventory sold
        try:
            inventory_mark_sold(
                product.inventory_item,
                actor=customer.email,
                notes=f"Order placed by {customer.email}",
            )
        except ValueError as e:
            raise CartError(str(e))

        # Update product listing status to mirror inventory
        product.listing_status = "sold_out"
        product.save(update_fields=["listing_status", "updated_at"])

        # Mark reservation converted
        session.reservation.status = Reservation.Status.CONVERTED
        session.reservation.save(update_fields=["status", "updated_at"])

        # Mark checkout session completed
        session.status = CheckoutSession.Status.COMPLETED
        session.save(update_fields=["status", "updated_at"])

        order = Order.objects.create(
            customer=customer,
            checkout_session=session,
            gemstone_id=product.gemstone_id,
            product_headline=product.headline,
            product_slug=product.slug,
            subtotal_usd=session.subtotal_usd,
            shipping_usd=session.shipping_usd,
            total_usd=session.total_usd,
            shipping_address=session.shipping_address,
            billing_address=session.billing_address,
        )

        OrderStatusLog.objects.create(
            order=order,
            from_status="",
            to_status=Order.Status.PENDING_PAYMENT,
            actor=customer.email,
            notes="Order placed.",
        )

    return order


def transition_order_status(
    order: Order,
    new_status: str,
    actor: str = "system",
    notes: str = "",
) -> Order:
    """Transition an order to a new status and log the change."""
    _ALLOWED_TRANSITIONS = {
        Order.Status.PENDING_PAYMENT: [
            Order.Status.CONFIRMED,
            Order.Status.CANCELLED,
        ],
        Order.Status.CONFIRMED: [
            Order.Status.PROCESSING,
            Order.Status.CANCELLED,
            Order.Status.REFUNDED,
        ],
        Order.Status.PROCESSING: [
            Order.Status.SHIPPED,
            Order.Status.CANCELLED,
            Order.Status.REFUNDED,
        ],
        Order.Status.SHIPPED: [
            Order.Status.DELIVERED,
            Order.Status.REFUNDED,
        ],
        Order.Status.DELIVERED: [
            Order.Status.REFUNDED,
        ],
        Order.Status.CANCELLED: [],
        Order.Status.REFUNDED: [],
    }

    allowed = _ALLOWED_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise CartError(
            f"Cannot transition order from '{order.status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    with transaction.atomic():
        from_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusLog.objects.create(
            order=order,
            from_status=from_status,
            to_status=new_status,
            actor=actor,
            notes=notes,
        )

    return order


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

def initiate_payment(order: Order, provider_name: str) -> tuple[Payment, dict]:
    """Create a pending Payment record and call the provider's initiate().

    Returns (payment, provider_data) where provider_data is whatever the
    adapter returns (e.g. a redirect URL or client secret).
    """
    from .payment_providers import get_provider

    if order.status != Order.Status.PENDING_PAYMENT:
        raise CartError(
            f"Order {order.order_ref} is not awaiting payment (status={order.status})."
        )

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        raise CartError(str(e))

    payment = Payment.objects.create(
        order=order,
        provider=provider_name,
        amount_usd=order.total_usd,
    )

    try:
        provider_data = provider.initiate(order)
    except Exception as e:
        payment.status = Payment.Status.FAILED
        payment.raw_response = {"error": str(e)}
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        raise CartError(f"Payment initiation failed: {e}")

    return payment, provider_data


def record_payment_result(payment: Payment, result) -> Payment:
    """Apply a PaymentResult to a Payment record and update the Order.

    On success: transitions Order to confirmed and stores payment_reference.
    On failure: marks Payment as failed, Order remains pending_payment.
    """
    with transaction.atomic():
        payment.provider_reference = result.provider_reference
        payment.raw_response = result.raw_response

        if result.success:
            payment.status = Payment.Status.SUCCEEDED
            payment.save(update_fields=[
                "status", "provider_reference", "raw_response", "updated_at"
            ])
            order = payment.order
            order.payment_reference = result.provider_reference
            order.save(update_fields=["payment_reference", "updated_at"])
            transition_order_status(
                order,
                Order.Status.CONFIRMED,
                actor="payment_system",
                notes=f"Payment confirmed via {payment.provider} ({result.provider_reference})",
            )
            _notify("order_notifications", "notify_order_confirmed", order)
            _notify("order_notifications", "notify_order_paid", order, payment)
        else:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=[
                "status", "provider_reference", "raw_response", "updated_at"
            ])

    return payment


# ---------------------------------------------------------------------------
# Shipment
# ---------------------------------------------------------------------------

_SHIPMENT_TRANSITIONS = {
    Shipment.Status.PENDING: [Shipment.Status.DISPATCHED],
    Shipment.Status.DISPATCHED: [Shipment.Status.IN_TRANSIT],
    Shipment.Status.IN_TRANSIT: [Shipment.Status.DELIVERED, Shipment.Status.RETURNED],
    Shipment.Status.DELIVERED: [],
    Shipment.Status.RETURNED: [],
}


def create_shipment(
    order: Order,
    carrier: str,
    tracking_number: str = "",
    tracking_url: str = "",
    estimated_delivery_date=None,
    notes: str = "",
    actor: str = "system",
) -> "Shipment":
    """Create a Shipment for an order and transition it to processing.

    Order must be in confirmed status. Transitions order to processing.
    """
    if order.status != Order.Status.CONFIRMED:
        raise CartError(
            f"Cannot create shipment for order {order.order_ref} (status={order.status}). "
            "Order must be confirmed."
        )

    if Shipment.objects.filter(order=order).exists():
        raise CartError(f"A shipment already exists for order {order.order_ref}.")

    if not carrier:
        raise CartError("carrier is required.")

    with transaction.atomic():
        shipment = Shipment.objects.create(
            order=order,
            carrier=carrier,
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            estimated_delivery_date=estimated_delivery_date,
            notes=notes,
        )
        transition_order_status(
            order,
            Order.Status.PROCESSING,
            actor=actor,
            notes=f"Shipment created via {carrier}.",
        )
        _notify("order_notifications", "notify_order_dispatched", order, shipment)

    return shipment


def update_shipment_status(
    shipment: "Shipment",
    new_status: str,
    actor: str = "system",
    notes: str = "",
    actual_delivery_date=None,
) -> "Shipment":
    """Transition a shipment to a new status and mirror to the order where applicable.

    dispatched  → order stays processing
    in_transit  → order transitions to shipped
    delivered   → order transitions to delivered
    returned    → order stays as-is (staff handles manually)
    """
    allowed = _SHIPMENT_TRANSITIONS.get(shipment.status, [])
    if new_status not in allowed:
        raise CartError(
            f"Cannot transition shipment from '{shipment.status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    with transaction.atomic():
        shipment.status = new_status
        if new_status == Shipment.Status.DELIVERED and actual_delivery_date:
            shipment.actual_delivery_date = actual_delivery_date
        shipment.save(update_fields=[
            f for f in ["status", "actual_delivery_date", "updated_at"]
            if f != "actual_delivery_date" or actual_delivery_date
        ])

        order = shipment.order
        if new_status == Shipment.Status.IN_TRANSIT:
            transition_order_status(order, Order.Status.SHIPPED, actor=actor, notes=notes)
        elif new_status == Shipment.Status.DELIVERED:
            transition_order_status(order, Order.Status.DELIVERED, actor=actor, notes=notes)
            _notify("order_notifications", "notify_order_delivered", order, shipment)

    return shipment


# ---------------------------------------------------------------------------
# Export & compliance
# ---------------------------------------------------------------------------

_EXPORT_COMPLIANCE_TRANSITIONS = {
    ExportRecord.ComplianceStatus.PENDING: [
        ExportRecord.ComplianceStatus.CLEARED,
        ExportRecord.ComplianceStatus.REJECTED,
    ],
    ExportRecord.ComplianceStatus.CLEARED: [],
    ExportRecord.ComplianceStatus.REJECTED: [
        ExportRecord.ComplianceStatus.PENDING,
    ],
}


def create_export_record(
    order: Order,
    destination_country: str,
    declared_value_usd,
    export_permit_number: str = "",
    customs_declaration_number: str = "",
    document_s3_keys: str = "",
    notes: str = "",
    actor: str = "system",
) -> ExportRecord:
    """Create an export record for an order and mark inventory as export-ready.

    Order must be in processing or shipped status.
    """
    from inventory.services import mark_export_ready as inventory_mark_export_ready

    if order.status not in [Order.Status.PROCESSING, Order.Status.SHIPPED]:
        raise CartError(
            f"Cannot create export record for order {order.order_ref} "
            f"(status={order.status}). Order must be processing or shipped."
        )

    if ExportRecord.objects.filter(order=order).exists():
        raise CartError(f"An export record already exists for order {order.order_ref}.")

    if not destination_country:
        raise CartError("destination_country is required.")

    if declared_value_usd is None:
        raise CartError("declared_value_usd is required.")

    with transaction.atomic():
        export_record = ExportRecord.objects.create(
            order=order,
            destination_country=destination_country,
            declared_value_usd=declared_value_usd,
            export_permit_number=export_permit_number,
            customs_declaration_number=customs_declaration_number,
            document_s3_keys=document_s3_keys,
            notes=notes,
        )
        try:
            inventory_item = order.checkout_session.reservation.product.inventory_item
            inventory_mark_export_ready(
                inventory_item,
                actor=actor,
                notes=f"Export record created for {order.order_ref}",
            )
        except Exception:
            pass  # inventory flag is best-effort; export record is the source of truth

    return export_record


def update_export_compliance(
    export_record: ExportRecord,
    new_status: str,
    notes: str = "",
) -> ExportRecord:
    """Transition an export record's compliance status."""
    allowed = _EXPORT_COMPLIANCE_TRANSITIONS.get(export_record.compliance_status, [])
    if new_status not in allowed:
        raise CartError(
            f"Cannot transition compliance from '{export_record.compliance_status}' "
            f"to '{new_status}'. Allowed: {allowed}"
        )
    export_record.compliance_status = new_status
    if notes:
        export_record.notes = notes
    export_record.save(update_fields=["compliance_status", "notes", "updated_at"])
    return export_record


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

_REFUNDABLE_STATUSES = [
    Order.Status.CONFIRMED,
    Order.Status.PROCESSING,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
]


def request_refund(order: Order, reason: str, requested_by: str = "system") -> Refund:
    """Create a pending Refund for an order and transition it to refunded.

    Raises CartError if:
    - The order is not in a refundable state
    - A refund already exists for this order
    - No succeeded payment exists to refund against
    """
    if order.status not in _REFUNDABLE_STATUSES:
        raise CartError(
            f"Order {order.order_ref} cannot be refunded (status={order.status})."
        )

    if Refund.objects.filter(order=order).exists():
        raise CartError(f"A refund already exists for order {order.order_ref}.")

    payment = (
        Payment.objects
        .filter(order=order, status=Payment.Status.SUCCEEDED)
        .order_by("-created_at")
        .first()
    )
    if not payment:
        raise CartError(f"No succeeded payment found for order {order.order_ref}.")

    with transaction.atomic():
        refund = Refund.objects.create(
            order=order,
            payment=payment,
            amount_usd=order.total_usd,
            reason=reason,
            requested_by=requested_by,
        )
        transition_order_status(
            order,
            Order.Status.REFUNDED,
            actor=requested_by,
            notes=f"Refund requested: {reason}",
        )

    return refund


def record_refund_result(
    refund: Refund,
    success: bool,
    provider_reference: str = "",
    raw_response: dict = None,
) -> Refund:
    """Update a Refund record after the provider processes it."""
    refund.provider_reference = provider_reference
    refund.raw_response = raw_response or {}
    refund.status = Refund.Status.SUCCEEDED if success else Refund.Status.FAILED
    refund.save(update_fields=["status", "provider_reference", "raw_response", "updated_at"])
    return refund
