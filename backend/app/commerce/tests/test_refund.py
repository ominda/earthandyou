import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Order, Payment, Refund
from commerce.services import (
    create_reservation, create_checkout_session, place_order,
    initiate_payment, record_payment_result, request_refund,
    record_refund_result, transition_order_status, CartError,
)
from commerce.payment_providers import PaymentResult
from commerce.webxpay import _build_signature


WEBXPAY_SETTINGS = {
    "WEBXPAY_MERCHANT_ID": "TEST_MERCHANT",
    "WEBXPAY_SECRET_KEY": "test-secret-key",
    "WEBXPAY_API_URL": "https://payment.webxpay.com/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!", is_staff=False):
    return Customer.objects.create_user(email=email, password=password, is_staff=is_staff)


def make_confirmed_order(customer, species_code="RF1"):
    species, _ = GemstoneSpecies.objects.get_or_create(
        code=species_code,
        defaults={"name": f"Species-{species_code}", "common_name": "Test"},
    )
    gemstone = PhysicalGemstone.objects.create(
        species=species, acquisition_date=datetime.date.today()
    )
    inventory = InventoryItem.objects.create(
        physical_gemstone=gemstone,
        listing_status=ListingStatus.ACTIVE,
        is_reserved=False,
        is_sold=False,
    )
    product = Product.objects.create(
        inventory_item=inventory,
        price_usd=Decimal("2000.00"),
        listing_status=ListingStatus.ACTIVE,
        value_tier=ValueTier.PREMIUM,
        headline="Test Gem",
    )
    reservation = create_reservation(customer, product.pk)
    address = CustomerAddress.objects.create(
        customer=customer,
        address_type="shipping",
        recipient_name="Ada Lovelace",
        line1="123 Gem St",
        city="Colombo",
        country="LK",
    )
    session = create_checkout_session(customer, reservation.pk, address.pk)
    order = place_order(customer, session.pk)

    # Simulate a succeeded payment to put order in confirmed state
    payment, _ = initiate_payment(order, "webxpay")
    result = PaymentResult(
        success=True,
        provider_reference="TXN-TEST-001",
        amount_usd=order.total_usd,
        raw_response={},
    )
    record_payment_result(payment, result)
    order.refresh_from_db()
    return order


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# request_refund service tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class RequestRefundServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_confirmed_order(self.customer, species_code="RS1")

    def test_creates_pending_refund(self):
        refund = request_refund(self.order, reason="Customer changed mind", requested_by="admin@example.com")
        self.assertEqual(refund.status, Refund.Status.PENDING)
        self.assertEqual(refund.amount_usd, self.order.total_usd)
        self.assertEqual(refund.reason, "Customer changed mind")
        self.assertEqual(refund.requested_by, "admin@example.com")

    def test_refund_linked_to_succeeded_payment(self):
        refund = request_refund(self.order, reason="Damaged item")
        payment = Payment.objects.get(order=self.order, status=Payment.Status.SUCCEEDED)
        self.assertEqual(refund.payment, payment)

    def test_transitions_order_to_refunded(self):
        request_refund(self.order, reason="Returned")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REFUNDED)

    def test_duplicate_refund_raises(self):
        request_refund(self.order, reason="First refund")
        with self.assertRaises(CartError):
            request_refund(self.order, reason="Second refund")

    def test_non_refundable_status_raises(self):
        # pending_payment order has no succeeded payment and wrong status
        species, _ = GemstoneSpecies.objects.get_or_create(
            code="RS2", defaults={"name": "Species-RS2", "common_name": "Test"}
        )
        gemstone = PhysicalGemstone.objects.create(
            species=species, acquisition_date=datetime.date.today()
        )
        inventory = InventoryItem.objects.create(
            physical_gemstone=gemstone,
            listing_status=ListingStatus.ACTIVE,
        )
        product = Product.objects.create(
            inventory_item=inventory,
            price_usd=Decimal("500.00"),
            listing_status=ListingStatus.ACTIVE,
        )
        reservation = create_reservation(self.customer, product.pk)
        address = CustomerAddress.objects.get(customer=self.customer)
        session = create_checkout_session(self.customer, reservation.pk, address.pk)
        pending_order = place_order(self.customer, session.pk)
        with self.assertRaises(CartError):
            request_refund(pending_order, reason="Should fail")

    def test_no_succeeded_payment_raises(self):
        # Manually force order to confirmed without a real payment
        species, _ = GemstoneSpecies.objects.get_or_create(
            code="RS3", defaults={"name": "Species-RS3", "common_name": "Test"}
        )
        gemstone = PhysicalGemstone.objects.create(
            species=species, acquisition_date=datetime.date.today()
        )
        inventory = InventoryItem.objects.create(
            physical_gemstone=gemstone,
            listing_status=ListingStatus.ACTIVE,
        )
        product = Product.objects.create(
            inventory_item=inventory,
            price_usd=Decimal("500.00"),
            listing_status=ListingStatus.ACTIVE,
        )
        reservation = create_reservation(self.customer, product.pk)
        address = CustomerAddress.objects.get(customer=self.customer)
        session = create_checkout_session(self.customer, reservation.pk, address.pk)
        order = place_order(self.customer, session.pk)
        # Force to confirmed without payment
        transition_order_status(order, Order.Status.CONFIRMED, actor="test")
        with self.assertRaises(CartError):
            request_refund(order, reason="No payment")

    def test_refundable_from_delivered_status(self):
        transition_order_status(self.order, Order.Status.PROCESSING)
        transition_order_status(self.order, Order.Status.SHIPPED)
        transition_order_status(self.order, Order.Status.DELIVERED)
        refund = request_refund(self.order, reason="Returned after delivery")
        self.assertIsNotNone(refund.pk)


# ---------------------------------------------------------------------------
# record_refund_result service tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class RecordRefundResultTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_confirmed_order(self.customer, species_code="RR1")
        self.refund = request_refund(self.order, reason="Test refund")

    def test_success_marks_refund_succeeded(self):
        refund = record_refund_result(
            self.refund, success=True,
            provider_reference="REF-001",
            raw_response={"status": "refunded"},
        )
        self.assertEqual(refund.status, Refund.Status.SUCCEEDED)
        self.assertEqual(refund.provider_reference, "REF-001")

    def test_failure_marks_refund_failed(self):
        refund = record_refund_result(self.refund, success=False, raw_response={"error": "declined"})
        self.assertEqual(refund.status, Refund.Status.FAILED)

    def test_raw_response_stored(self):
        raw = {"gateway": "webxpay", "refund_id": "R-999"}
        refund = record_refund_result(self.refund, success=True, raw_response=raw)
        self.assertEqual(refund.raw_response, raw)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class OrderRefundAPITests(TestCase):

    def setUp(self):
        self.staff = make_customer("staff@example.com", is_staff=True)
        self.customer = make_customer()
        self.staff_client = auth_client(self.staff)
        self.customer_client = auth_client(self.customer)
        self.order = make_confirmed_order(self.customer, species_code="AP1")

    def test_staff_can_request_refund(self):
        res = self.staff_client.post(
            reverse("order-refund", args=[self.order.pk]),
            {"reason": "Customer returned item"},
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], Refund.Status.PENDING)
        self.assertIn("reason", res.data)

    def test_non_staff_cannot_request_refund(self):
        res = self.customer_client.post(
            reverse("order-refund", args=[self.order.pk]),
            {"reason": "I want a refund"},
        )
        self.assertEqual(res.status_code, 403)

    def test_missing_reason_returns_400(self):
        res = self.staff_client.post(reverse("order-refund", args=[self.order.pk]), {})
        self.assertEqual(res.status_code, 400)

    def test_unknown_order_returns_404(self):
        res = self.staff_client.post(
            reverse("order-refund", args=[99999]),
            {"reason": "Test"},
        )
        self.assertEqual(res.status_code, 404)

    def test_duplicate_refund_returns_400(self):
        self.staff_client.post(
            reverse("order-refund", args=[self.order.pk]),
            {"reason": "First"},
        )
        res = self.staff_client.post(
            reverse("order-refund", args=[self.order.pk]),
            {"reason": "Second"},
        )
        self.assertEqual(res.status_code, 400)

    def test_requires_auth(self):
        res = APIClient().post(
            reverse("order-refund", args=[self.order.pk]),
            {"reason": "Test"},
        )
        self.assertEqual(res.status_code, 401)
