import datetime
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Order, Shipment
from commerce.services import (
    create_reservation, create_checkout_session, place_order,
    initiate_payment, record_payment_result,
    create_shipment, update_shipment_status,
)
from commerce.payment_providers import PaymentResult


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


def make_confirmed_order(customer, species_code="TK1"):
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


# ---------------------------------------------------------------------------
# Tracking API tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class OrderTrackingAPITests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_confirmed_order(self.customer, species_code="TK1")
        self.client = APIClient()

    def test_returns_tracking_summary_by_order_ref(self):
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["order_ref"], self.order.order_ref)
        self.assertEqual(res.data["status"], Order.Status.CONFIRMED)

    def test_no_auth_required(self):
        # Unauthenticated client can access tracking
        res = APIClient().get(reverse("order-tracking", args=[self.order.order_ref]))
        self.assertEqual(res.status_code, 200)

    def test_unknown_order_ref_returns_404(self):
        res = self.client.get(reverse("order-tracking", args=["ORD-9999-999999"]))
        self.assertEqual(res.status_code, 404)

    def test_response_contains_expected_fields(self):
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        for field in ["order_ref", "gemstone_id", "product_headline", "status", "created_at", "shipment", "timeline"]:
            self.assertIn(field, res.data)

    def test_shipment_is_none_before_dispatch(self):
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        self.assertIsNone(res.data["shipment"])

    def test_shipment_populated_after_creation(self):
        create_shipment(self.order, carrier="DHL", tracking_number="TRK123")
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        self.assertIsNotNone(res.data["shipment"])
        self.assertEqual(res.data["shipment"]["carrier"], "DHL")
        self.assertEqual(res.data["shipment"]["tracking_number"], "TRK123")

    def test_shipment_status_updates_reflected(self):
        shipment = create_shipment(self.order, carrier="FedEx")
        update_shipment_status(shipment, Shipment.Status.DISPATCHED)
        update_shipment_status(shipment, Shipment.Status.IN_TRANSIT)
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        self.assertEqual(res.data["shipment"]["status"], Shipment.Status.IN_TRANSIT)
        self.assertEqual(res.data["status"], Order.Status.SHIPPED)

    def test_timeline_contains_status_history(self):
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        statuses = [entry["status"] for entry in res.data["timeline"]]
        # Order was placed (pending_payment) then confirmed via payment
        self.assertIn(Order.Status.PENDING_PAYMENT, statuses)
        self.assertIn(Order.Status.CONFIRMED, statuses)

    def test_timeline_grows_with_transitions(self):
        create_shipment(self.order, carrier="DHL")
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        statuses = [entry["status"] for entry in res.data["timeline"]]
        self.assertIn(Order.Status.PROCESSING, statuses)

    def test_does_not_expose_pricing_or_addresses(self):
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        for sensitive_field in ["subtotal_usd", "total_usd", "shipping_address", "billing_address", "payment_reference"]:
            self.assertNotIn(sensitive_field, res.data)

    def test_delivered_order_shows_actual_delivery_date(self):
        shipment = create_shipment(self.order, carrier="DHL")
        update_shipment_status(shipment, Shipment.Status.DISPATCHED)
        update_shipment_status(shipment, Shipment.Status.IN_TRANSIT)
        delivery_date = datetime.date(2026, 12, 26)
        update_shipment_status(
            shipment, Shipment.Status.DELIVERED,
            actual_delivery_date=delivery_date,
        )
        res = self.client.get(reverse("order-tracking", args=[self.order.order_ref]))
        self.assertEqual(res.data["shipment"]["actual_delivery_date"], delivery_date)
        self.assertEqual(res.data["status"], Order.Status.DELIVERED)
