import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Order, Payment
from commerce.services import (
    create_reservation, create_checkout_session, place_order,
    initiate_payment, record_payment_result, CartError,
)
from commerce.payment_providers import (
    BasePaymentProvider, PaymentResult, register_provider, get_provider,
)


# ---------------------------------------------------------------------------
# Stub provider for testing
# ---------------------------------------------------------------------------

class StubProvider(BasePaymentProvider):
    name = "stub"

    def initiate(self, order) -> dict:
        return {"payment_url": f"https://stub.example.com/pay/{order.order_ref}"}

    def verify(self, payload: dict) -> PaymentResult:
        success = payload.get("status") == "success"
        return PaymentResult(
            success=success,
            provider_reference=payload.get("txn_id", ""),
            amount_usd=Decimal(str(payload.get("amount", "0"))),
            raw_response=payload,
            failure_reason="" if success else payload.get("reason", "declined"),
        )


class FailingProvider(BasePaymentProvider):
    name = "stub_fail"

    def initiate(self, order) -> dict:
        raise RuntimeError("Gateway unreachable")

    def verify(self, payload: dict) -> PaymentResult:
        return PaymentResult(
            success=False,
            provider_reference="",
            amount_usd=Decimal("0"),
            raw_response=payload,
            failure_reason="always fails",
        )


register_provider(StubProvider())
register_provider(FailingProvider())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def make_product(species_code="PAY"):
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
    return Product.objects.create(
        inventory_item=inventory,
        price_usd=Decimal("2000.00"),
        listing_status=ListingStatus.ACTIVE,
        value_tier=ValueTier.PREMIUM,
        headline="Test Gem",
    )


def make_order(customer, species_code="PAY"):
    product = make_product(species_code)
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


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# Provider registry tests
# ---------------------------------------------------------------------------

class ProviderRegistryTests(TestCase):

    def test_get_registered_provider(self):
        provider = get_provider("stub")
        self.assertIsInstance(provider, StubProvider)

    def test_get_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            get_provider("nonexistent")


# ---------------------------------------------------------------------------
# initiate_payment service tests
# ---------------------------------------------------------------------------

class InitiatePaymentTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_order(self.customer, species_code="IP1")

    def test_creates_pending_payment(self):
        payment, _ = initiate_payment(self.order, "stub")
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.provider, "stub")
        self.assertEqual(payment.amount_usd, self.order.total_usd)

    def test_returns_provider_data(self):
        _, provider_data = initiate_payment(self.order, "stub")
        self.assertIn("payment_url", provider_data)
        self.assertIn(self.order.order_ref, provider_data["payment_url"])

    def test_non_pending_payment_order_raises(self):
        from commerce.services import transition_order_status
        transition_order_status(self.order, Order.Status.CONFIRMED)
        with self.assertRaises(CartError):
            initiate_payment(self.order, "stub")

    def test_unknown_provider_raises(self):
        with self.assertRaises(CartError):
            initiate_payment(self.order, "unknown_provider")

    def test_provider_initiate_failure_marks_payment_failed(self):
        with self.assertRaises(CartError):
            initiate_payment(self.order, "stub_fail")
        payment = Payment.objects.filter(order=self.order).first()
        self.assertEqual(payment.status, Payment.Status.FAILED)


# ---------------------------------------------------------------------------
# record_payment_result service tests
# ---------------------------------------------------------------------------

class RecordPaymentResultTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_order(self.customer, species_code="RP1")
        self.payment, _ = initiate_payment(self.order, "stub")

    def test_success_marks_payment_succeeded(self):
        result = PaymentResult(
            success=True,
            provider_reference="TXN-001",
            amount_usd=self.order.total_usd,
            raw_response={"status": "success", "txn_id": "TXN-001"},
        )
        payment = record_payment_result(self.payment, result)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(payment.provider_reference, "TXN-001")

    def test_success_transitions_order_to_confirmed(self):
        result = PaymentResult(
            success=True,
            provider_reference="TXN-002",
            amount_usd=self.order.total_usd,
            raw_response={},
        )
        record_payment_result(self.payment, result)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_success_stores_payment_reference_on_order(self):
        result = PaymentResult(
            success=True,
            provider_reference="TXN-003",
            amount_usd=self.order.total_usd,
            raw_response={},
        )
        record_payment_result(self.payment, result)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_reference, "TXN-003")

    def test_failure_marks_payment_failed(self):
        result = PaymentResult(
            success=False,
            provider_reference="",
            amount_usd=self.order.total_usd,
            raw_response={"reason": "insufficient_funds"},
            failure_reason="insufficient_funds",
        )
        payment = record_payment_result(self.payment, result)
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_failure_leaves_order_pending_payment(self):
        result = PaymentResult(
            success=False,
            provider_reference="",
            amount_usd=self.order.total_usd,
            raw_response={},
            failure_reason="declined",
        )
        record_payment_result(self.payment, result)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

    def test_raw_response_is_stored(self):
        raw = {"gateway": "stub", "code": "00", "txn_id": "TXN-004"}
        result = PaymentResult(
            success=True,
            provider_reference="TXN-004",
            amount_usd=self.order.total_usd,
            raw_response=raw,
        )
        payment = record_payment_result(self.payment, result)
        self.assertEqual(payment.raw_response, raw)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class OrderPayAPITests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)
        self.order = make_order(self.customer, species_code="AP1")

    def test_initiate_payment_returns_201(self):
        res = self.client.post(
            reverse("order-pay", args=[self.order.pk]),
            {"provider": "stub"},
        )
        self.assertEqual(res.status_code, 201)
        self.assertIn("payment", res.data)
        self.assertIn("provider_data", res.data)
        self.assertEqual(res.data["payment"]["status"], Payment.Status.PENDING)

    def test_missing_provider_returns_400(self):
        res = self.client.post(reverse("order-pay", args=[self.order.pk]), {})
        self.assertEqual(res.status_code, 400)

    def test_unknown_provider_returns_400(self):
        res = self.client.post(
            reverse("order-pay", args=[self.order.pk]),
            {"provider": "nonexistent"},
        )
        self.assertEqual(res.status_code, 400)

    def test_other_customers_order_returns_404(self):
        other = make_customer("other@example.com")
        other_order = make_order(other, species_code="AP2")
        res = self.client.post(
            reverse("order-pay", args=[other_order.pk]),
            {"provider": "stub"},
        )
        self.assertEqual(res.status_code, 404)

    def test_requires_auth(self):
        res = APIClient().post(reverse("order-pay", args=[self.order.pk]), {"provider": "stub"})
        self.assertEqual(res.status_code, 401)
