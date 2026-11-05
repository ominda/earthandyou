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
    create_shipment, update_shipment_status, transition_order_status, CartError,
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

def make_customer(email="buyer@example.com", password="StrongPass1!", is_staff=False):
    return Customer.objects.create_user(email=email, password=password, is_staff=is_staff)


def make_confirmed_order(customer, species_code="SM1"):
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


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# create_shipment service tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class CreateShipmentServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_confirmed_order(self.customer, species_code="CS1")

    def test_creates_shipment_with_pending_status(self):
        shipment = create_shipment(self.order, carrier="DHL")
        self.assertEqual(shipment.carrier, "DHL")
        self.assertEqual(shipment.status, Shipment.Status.PENDING)
        self.assertEqual(shipment.order, self.order)

    def test_transitions_order_to_processing(self):
        create_shipment(self.order, carrier="FedEx")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PROCESSING)

    def test_stores_tracking_fields(self):
        shipment = create_shipment(
            self.order,
            carrier="DHL",
            tracking_number="1Z999AA10123456784",
            tracking_url="https://track.dhl.com/1Z999AA10123456784",
            estimated_delivery_date=datetime.date(2026, 12, 25),
        )
        self.assertEqual(shipment.tracking_number, "1Z999AA10123456784")
        self.assertEqual(shipment.tracking_url, "https://track.dhl.com/1Z999AA10123456784")
        self.assertEqual(shipment.estimated_delivery_date, datetime.date(2026, 12, 25))

    def test_raises_if_order_not_confirmed(self):
        transition_order_status(self.order, Order.Status.PROCESSING, actor="test")
        with self.assertRaises(CartError):
            create_shipment(self.order, carrier="DHL")

    def test_raises_if_carrier_missing(self):
        with self.assertRaises(CartError):
            create_shipment(self.order, carrier="")

    def test_raises_on_duplicate_shipment(self):
        create_shipment(self.order, carrier="DHL")
        with self.assertRaises(CartError):
            create_shipment(self.order, carrier="FedEx")


# ---------------------------------------------------------------------------
# update_shipment_status service tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class UpdateShipmentStatusServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_confirmed_order(self.customer, species_code="US1")
        self.shipment = create_shipment(self.order, carrier="DHL")

    def test_pending_to_dispatched(self):
        shipment = update_shipment_status(self.shipment, Shipment.Status.DISPATCHED)
        self.assertEqual(shipment.status, Shipment.Status.DISPATCHED)

    def test_dispatched_to_in_transit_transitions_order_to_shipped(self):
        update_shipment_status(self.shipment, Shipment.Status.DISPATCHED)
        update_shipment_status(self.shipment, Shipment.Status.IN_TRANSIT)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)

    def test_in_transit_to_delivered_transitions_order_to_delivered(self):
        update_shipment_status(self.shipment, Shipment.Status.DISPATCHED)
        update_shipment_status(self.shipment, Shipment.Status.IN_TRANSIT)
        delivery_date = datetime.date(2026, 12, 26)
        update_shipment_status(
            self.shipment, Shipment.Status.DELIVERED,
            actual_delivery_date=delivery_date,
        )
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.actual_delivery_date, delivery_date)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)

    def test_in_transit_to_returned(self):
        update_shipment_status(self.shipment, Shipment.Status.DISPATCHED)
        update_shipment_status(self.shipment, Shipment.Status.IN_TRANSIT)
        shipment = update_shipment_status(self.shipment, Shipment.Status.RETURNED)
        self.assertEqual(shipment.status, Shipment.Status.RETURNED)

    def test_invalid_transition_raises(self):
        with self.assertRaises(CartError):
            update_shipment_status(self.shipment, Shipment.Status.DELIVERED)

    def test_terminal_status_raises(self):
        update_shipment_status(self.shipment, Shipment.Status.DISPATCHED)
        update_shipment_status(self.shipment, Shipment.Status.IN_TRANSIT)
        update_shipment_status(self.shipment, Shipment.Status.DELIVERED)
        with self.assertRaises(CartError):
            update_shipment_status(self.shipment, Shipment.Status.IN_TRANSIT)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class OrderShipmentAPITests(TestCase):

    def setUp(self):
        self.staff = make_customer("staff@example.com", is_staff=True)
        self.customer = make_customer()
        self.staff_client = auth_client(self.staff)
        self.customer_client = auth_client(self.customer)
        self.order = make_confirmed_order(self.customer, species_code="AP1")

    def test_staff_can_create_shipment(self):
        res = self.staff_client.post(
            reverse("order-shipment", args=[self.order.pk]),
            {"carrier": "DHL", "tracking_number": "TRK001"},
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["carrier"], "DHL")
        self.assertEqual(res.data["status"], Shipment.Status.PENDING)

    def test_non_staff_cannot_create_shipment(self):
        res = self.customer_client.post(
            reverse("order-shipment", args=[self.order.pk]),
            {"carrier": "DHL"},
        )
        self.assertEqual(res.status_code, 403)

    def test_customer_can_get_their_shipment(self):
        create_shipment(self.order, carrier="DHL")
        res = self.customer_client.get(reverse("order-shipment", args=[self.order.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["carrier"], "DHL")

    def test_customer_cannot_get_other_customers_shipment(self):
        other = make_customer("other@example.com")
        other_order = make_confirmed_order(other, species_code="OT1")
        create_shipment(other_order, carrier="FedEx")
        res = self.customer_client.get(reverse("order-shipment", args=[other_order.pk]))
        self.assertEqual(res.status_code, 404)

    def test_get_returns_404_when_no_shipment(self):
        res = self.customer_client.get(reverse("order-shipment", args=[self.order.pk]))
        self.assertEqual(res.status_code, 404)

    def test_staff_can_update_shipment_status(self):
        create_shipment(self.order, carrier="DHL")
        res = self.staff_client.put(
            reverse("order-shipment", args=[self.order.pk]),
            {"status": Shipment.Status.DISPATCHED},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], Shipment.Status.DISPATCHED)

    def test_invalid_status_transition_returns_400(self):
        create_shipment(self.order, carrier="DHL")
        res = self.staff_client.put(
            reverse("order-shipment", args=[self.order.pk]),
            {"status": Shipment.Status.DELIVERED},
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_status_on_put_returns_400(self):
        create_shipment(self.order, carrier="DHL")
        res = self.staff_client.put(
            reverse("order-shipment", args=[self.order.pk]),
            {},
        )
        self.assertEqual(res.status_code, 400)

    def test_unauthenticated_cannot_access(self):
        res = APIClient().get(reverse("order-shipment", args=[self.order.pk]))
        self.assertEqual(res.status_code, 401)

    def test_unknown_order_returns_404(self):
        res = self.staff_client.post(
            reverse("order-shipment", args=[99999]),
            {"carrier": "DHL"},
        )
        self.assertEqual(res.status_code, 404)
