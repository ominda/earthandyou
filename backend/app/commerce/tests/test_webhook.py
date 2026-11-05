import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Order, Payment
from commerce.services import (
    create_reservation, create_checkout_session, place_order, initiate_payment,
)
from commerce.webxpay import _build_signature


WEBXPAY_SETTINGS = {
    "WEBXPAY_MERCHANT_ID": "TEST_MERCHANT",
    "WEBXPAY_SECRET_KEY": "test-secret-key",
    "WEBXPAY_API_URL": "https://payment.webxpay.com/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def make_order(customer, species_code="WH1"):
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
    return place_order(customer, session.pk)


def make_payload(order, secret, status="SUCCESS", txn_id="TXN-001", tamper_sig=False):
    amount = f"{order.total_usd:.2f}"
    currency = "USD"
    sig = _build_signature(secret, order.order_ref, amount, currency)
    if tamper_sig:
        sig = "0" * 64
    return {
        "order_ref": order.order_ref,
        "amount": amount,
        "currency": currency,
        "status": status,
        "txn_id": txn_id,
        "signature": sig,
    }


# ---------------------------------------------------------------------------
# Webhook tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class WebXPayWebhookTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        self.order = make_order(self.customer, species_code="WH1")
        initiate_payment(self.order, "webxpay")
        self.secret = WEBXPAY_SETTINGS["WEBXPAY_SECRET_KEY"]
        self.url = reverse("webhook-webxpay")

    def test_successful_payment_returns_200(self):
        payload = make_payload(self.order, self.secret)
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 200)

    def test_successful_payment_marks_payment_succeeded(self):
        payload = make_payload(self.order, self.secret)
        self.client.post(self.url, payload, format="json")
        payment = Payment.objects.get(order=self.order, provider="webxpay")
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(payment.provider_reference, "TXN-001")

    def test_successful_payment_confirms_order(self):
        payload = make_payload(self.order, self.secret)
        self.client.post(self.url, payload, format="json")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_successful_payment_stores_payment_reference(self):
        payload = make_payload(self.order, self.secret, txn_id="TXN-REF-999")
        self.client.post(self.url, payload, format="json")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_reference, "TXN-REF-999")

    def test_failed_payment_returns_200(self):
        # WEBXPAY expects 200 even on failed payments so it doesn't retry
        payload = make_payload(self.order, self.secret, status="FAILED")
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 200)

    def test_failed_payment_marks_payment_failed(self):
        payload = make_payload(self.order, self.secret, status="FAILED")
        self.client.post(self.url, payload, format="json")
        payment = Payment.objects.get(order=self.order, provider="webxpay")
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_failed_payment_leaves_order_pending(self):
        payload = make_payload(self.order, self.secret, status="FAILED")
        self.client.post(self.url, payload, format="json")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

    def test_invalid_signature_returns_200_but_marks_failed(self):
        # Still 200 so WEBXPAY doesn't retry a tampered payload
        payload = make_payload(self.order, self.secret, tamper_sig=True)
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 200)
        payment = Payment.objects.get(order=self.order, provider="webxpay")
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_invalid_signature_does_not_confirm_order(self):
        payload = make_payload(self.order, self.secret, tamper_sig=True)
        self.client.post(self.url, payload, format="json")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

    def test_missing_order_ref_returns_400(self):
        res = self.client.post(self.url, {"status": "SUCCESS"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_unknown_order_ref_returns_400(self):
        payload = make_payload(self.order, self.secret)
        payload["order_ref"] = "ORD-9999-999999"
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 400)

    def test_idempotent_duplicate_delivery(self):
        payload = make_payload(self.order, self.secret)
        self.client.post(self.url, payload, format="json")
        # Second delivery of the same webhook
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 200)
        # Still only one succeeded payment
        self.assertEqual(
            Payment.objects.filter(order=self.order, status=Payment.Status.SUCCEEDED).count(), 1
        )
        # Order status unchanged
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_no_auth_required(self):
        # Webhook must be accessible without any authentication header
        payload = make_payload(self.order, self.secret)
        client = APIClient()  # no credentials
        res = client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, 200)
