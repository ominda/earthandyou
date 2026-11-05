import datetime
import hashlib
import hmac
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from catalog.models import GemstoneSpecies, Product, ValueTier
from commerce.models import Order
from commerce.payment_providers import get_provider, PaymentResult
from commerce.services import create_reservation, create_checkout_session, place_order
from commerce.webxpay import WebXPayProvider, _build_signature, _sign
from customers.models import Customer, CustomerAddress
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus


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


def make_order(customer, species_code="WXP"):
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
        price_usd=Decimal("3000.00"),
        listing_status=ListingStatus.ACTIVE,
        value_tier=ValueTier.LUXURY,
        headline="Test Sapphire",
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


def make_valid_payload(order, secret, status="SUCCESS", txn_id="TXN-WEBX-001"):
    amount = f"{order.total_usd:.2f}"
    currency = "USD"
    sig = _build_signature(secret, order.order_ref, amount, currency)
    return {
        "order_ref": order.order_ref,
        "amount": amount,
        "currency": currency,
        "status": status,
        "txn_id": txn_id,
        "signature": sig,
    }


# ---------------------------------------------------------------------------
# Signature utility tests
# ---------------------------------------------------------------------------

class SignatureTests(TestCase):

    def test_sign_produces_hex_string(self):
        result = _sign("secret", "message")
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

    def test_sign_is_deterministic(self):
        self.assertEqual(_sign("secret", "msg"), _sign("secret", "msg"))

    def test_sign_differs_with_different_secret(self):
        self.assertNotEqual(_sign("secret1", "msg"), _sign("secret2", "msg"))

    def test_build_signature_format(self):
        sig = _build_signature("secret", "ORD-2026-000001", "3050.00", "USD")
        expected = _sign("secret", "ORD-2026-000001|3050.00|USD")
        self.assertEqual(sig, expected)


# ---------------------------------------------------------------------------
# Provider registration
# ---------------------------------------------------------------------------

class WebXPayRegistrationTests(TestCase):

    def test_webxpay_is_registered(self):
        provider = get_provider("webxpay")
        self.assertIsInstance(provider, WebXPayProvider)


# ---------------------------------------------------------------------------
# initiate() tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class WebXPayInitiateTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_order(self.customer, species_code="WI1")
        self.provider = WebXPayProvider()

    def test_returns_payment_url(self):
        result = self.provider.initiate(self.order)
        self.assertEqual(result["payment_url"], WEBXPAY_SETTINGS["WEBXPAY_API_URL"])

    def test_params_contain_required_fields(self):
        result = self.provider.initiate(self.order)
        params = result["params"]
        for field in ["merchant_id", "order_ref", "amount", "currency", "signature"]:
            self.assertIn(field, params)

    def test_params_merchant_id(self):
        result = self.provider.initiate(self.order)
        self.assertEqual(result["params"]["merchant_id"], "TEST_MERCHANT")

    def test_params_order_ref(self):
        result = self.provider.initiate(self.order)
        self.assertEqual(result["params"]["order_ref"], self.order.order_ref)

    def test_params_amount(self):
        result = self.provider.initiate(self.order)
        self.assertEqual(result["params"]["amount"], f"{self.order.total_usd:.2f}")

    def test_params_currency_is_usd(self):
        result = self.provider.initiate(self.order)
        self.assertEqual(result["params"]["currency"], "USD")

    def test_signature_is_valid(self):
        result = self.provider.initiate(self.order)
        params = result["params"]
        expected = _build_signature(
            WEBXPAY_SETTINGS["WEBXPAY_SECRET_KEY"],
            params["order_ref"],
            params["amount"],
            params["currency"],
        )
        self.assertEqual(params["signature"], expected)

    def test_missing_credentials_raises(self):
        with override_settings(WEBXPAY_MERCHANT_ID="", WEBXPAY_SECRET_KEY=""):
            with self.assertRaises(ValueError):
                self.provider.initiate(self.order)


# ---------------------------------------------------------------------------
# verify() tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class WebXPayVerifyTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_order(self.customer, species_code="WV1")
        self.provider = WebXPayProvider()
        self.secret = WEBXPAY_SETTINGS["WEBXPAY_SECRET_KEY"]

    def test_valid_success_payload(self):
        payload = make_valid_payload(self.order, self.secret)
        result = self.provider.verify(payload)
        self.assertTrue(result.success)
        self.assertEqual(result.provider_reference, "TXN-WEBX-001")
        self.assertEqual(result.amount_usd, self.order.total_usd)

    def test_valid_failed_payment(self):
        payload = make_valid_payload(self.order, self.secret, status="FAILED")
        result = self.provider.verify(payload)
        self.assertFalse(result.success)
        self.assertIn("FAILED", result.failure_reason)

    def test_invalid_signature_returns_failure(self):
        payload = make_valid_payload(self.order, self.secret)
        payload["signature"] = "0" * 64  # tampered
        result = self.provider.verify(payload)
        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, "Invalid signature")

    def test_tampered_amount_fails_signature(self):
        payload = make_valid_payload(self.order, self.secret)
        payload["amount"] = "1.00"  # tampered amount
        result = self.provider.verify(payload)
        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, "Invalid signature")

    def test_raw_response_is_stored(self):
        payload = make_valid_payload(self.order, self.secret)
        result = self.provider.verify(payload)
        self.assertEqual(result.raw_response, payload)

    def test_verify_never_raises(self):
        # Even a completely empty payload should not raise
        result = self.provider.verify({})
        self.assertFalse(result.success)

    def test_status_case_insensitive(self):
        payload = make_valid_payload(self.order, self.secret, status="success")
        result = self.provider.verify(payload)
        self.assertTrue(result.success)
