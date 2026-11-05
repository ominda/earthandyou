import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Reservation, CheckoutSession, Order
from commerce.services import (
    create_reservation, create_checkout_session, place_order,
    transition_order_status, CartError,
)


# ---------------------------------------------------------------------------
# Helpers (shared with test_checkout.py pattern)
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def make_product(price=1000, species_code="ORD", value_tier=ValueTier.STANDARD):
    species, _ = GemstoneSpecies.objects.get_or_create(
        code=species_code,
        defaults={"name": f"Species-{species_code}", "common_name": "Test"},
    )
    gemstone = PhysicalGemstone.objects.create(species=species, acquisition_date=datetime.date.today())
    inventory = InventoryItem.objects.create(
        physical_gemstone=gemstone,
        listing_status=ListingStatus.ACTIVE,
        is_reserved=False,
        is_sold=False,
    )
    return Product.objects.create(
        inventory_item=inventory,
        price_usd=price,
        listing_status=ListingStatus.ACTIVE,
        value_tier=value_tier,
        headline="Test Gemstone",
    )


def make_address(customer):
    return CustomerAddress.objects.create(
        customer=customer,
        address_type="shipping",
        recipient_name="Ada Lovelace",
        line1="123 Gem Street",
        city="Colombo",
        country="LK",
    )


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


def make_checkout_session(customer, species_code="ORD"):
    product = make_product(species_code=species_code)
    reservation = create_reservation(customer, product.pk)
    address = make_address(customer)
    session = create_checkout_session(customer, reservation.pk, address.pk)
    return session


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------

class PlaceOrderServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.session = make_checkout_session(self.customer, species_code="PO1")

    def test_place_order_creates_order(self):
        order = place_order(self.customer, self.session.pk)
        self.assertIsNotNone(order.pk)
        self.assertTrue(order.order_ref.startswith("ORD-"))
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)

    def test_order_snapshots_product_data(self):
        order = place_order(self.customer, self.session.pk)
        self.assertEqual(order.subtotal_usd, self.session.subtotal_usd)
        self.assertEqual(order.total_usd, self.session.total_usd)
        self.assertEqual(order.shipping_address, self.session.shipping_address)

    def test_place_order_marks_inventory_sold(self):
        product = self.session.reservation.product
        order = place_order(self.customer, self.session.pk)
        product.inventory_item.refresh_from_db()
        self.assertTrue(product.inventory_item.is_sold)
        self.assertFalse(product.inventory_item.is_reserved)

    def test_place_order_marks_reservation_converted(self):
        order = place_order(self.customer, self.session.pk)
        self.session.reservation.refresh_from_db()
        self.assertEqual(self.session.reservation.status, Reservation.Status.CONVERTED)

    def test_place_order_marks_session_completed(self):
        order = place_order(self.customer, self.session.pk)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, CheckoutSession.Status.COMPLETED)

    def test_place_order_creates_status_log(self):
        order = place_order(self.customer, self.session.pk)
        self.assertEqual(order.status_logs.count(), 1)
        log = order.status_logs.first()
        self.assertEqual(log.to_status, Order.Status.PENDING_PAYMENT)

    def test_duplicate_order_raises(self):
        place_order(self.customer, self.session.pk)
        with self.assertRaises(CartError):
            place_order(self.customer, self.session.pk)

    def test_invalid_session_raises(self):
        with self.assertRaises(CartError):
            place_order(self.customer, 99999)

    def test_expired_session_raises(self):
        CheckoutSession.objects.filter(pk=self.session.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
        self.session.refresh_from_db()
        with self.assertRaises(CartError):
            place_order(self.customer, self.session.pk)

    def test_other_customers_session_raises(self):
        other = make_customer("other@example.com")
        with self.assertRaises(CartError):
            place_order(other, self.session.pk)


# ---------------------------------------------------------------------------
# Order status transition tests
# ---------------------------------------------------------------------------

class OrderStatusTransitionTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        session = make_checkout_session(self.customer, species_code="ST1")
        self.order = place_order(self.customer, session.pk)

    def test_pending_payment_to_confirmed(self):
        order = transition_order_status(self.order, Order.Status.CONFIRMED, actor="admin@example.com")
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_confirmed_to_processing(self):
        transition_order_status(self.order, Order.Status.CONFIRMED)
        order = transition_order_status(self.order, Order.Status.PROCESSING)
        self.assertEqual(order.status, Order.Status.PROCESSING)

    def test_processing_to_shipped(self):
        transition_order_status(self.order, Order.Status.CONFIRMED)
        transition_order_status(self.order, Order.Status.PROCESSING)
        order = transition_order_status(self.order, Order.Status.SHIPPED)
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_shipped_to_delivered(self):
        transition_order_status(self.order, Order.Status.CONFIRMED)
        transition_order_status(self.order, Order.Status.PROCESSING)
        transition_order_status(self.order, Order.Status.SHIPPED)
        order = transition_order_status(self.order, Order.Status.DELIVERED)
        self.assertEqual(order.status, Order.Status.DELIVERED)

    def test_invalid_transition_raises(self):
        with self.assertRaises(CartError):
            transition_order_status(self.order, Order.Status.SHIPPED)

    def test_cancelled_is_terminal(self):
        transition_order_status(self.order, Order.Status.CANCELLED)
        with self.assertRaises(CartError):
            transition_order_status(self.order, Order.Status.CONFIRMED)

    def test_each_transition_appends_log(self):
        transition_order_status(self.order, Order.Status.CONFIRMED)
        transition_order_status(self.order, Order.Status.CANCELLED)
        # 1 initial log from place_order + 2 transitions
        self.assertEqual(self.order.status_logs.count(), 3)

    def test_status_log_is_immutable(self):
        log = self.order.status_logs.first()
        log.notes = "tampered"
        with self.assertRaises(ValueError):
            log.save()


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class OrderAPITests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)
        self.session = make_checkout_session(self.customer, species_code="AP1")

    def test_place_order_returns_201(self):
        res = self.client.post(reverse("orders"), {"checkout_session_id": self.session.pk})
        self.assertEqual(res.status_code, 201)
        self.assertIn("order_ref", res.data)
        self.assertEqual(res.data["status"], Order.Status.PENDING_PAYMENT)

    def test_place_order_missing_field_returns_400(self):
        res = self.client.post(reverse("orders"), {})
        self.assertEqual(res.status_code, 400)

    def test_place_order_invalid_session_returns_400(self):
        res = self.client.post(reverse("orders"), {"checkout_session_id": 99999})
        self.assertEqual(res.status_code, 400)

    def test_list_orders(self):
        self.client.post(reverse("orders"), {"checkout_session_id": self.session.pk})
        res = self.client.get(reverse("orders"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_get_order_detail(self):
        create_res = self.client.post(reverse("orders"), {"checkout_session_id": self.session.pk})
        pk = create_res.data["id"]
        res = self.client.get(reverse("order-detail", args=[pk]))
        self.assertEqual(res.status_code, 200)
        self.assertIn("status_logs", res.data)
        self.assertEqual(len(res.data["status_logs"]), 1)

    def test_cannot_access_other_customers_order(self):
        other = make_customer("other@example.com")
        other_session = make_checkout_session(other, species_code="AP2")
        other_order = place_order(other, other_session.pk)
        res = self.client.get(reverse("order-detail", args=[other_order.pk]))
        self.assertEqual(res.status_code, 404)

    def test_orders_require_auth(self):
        res = APIClient().get(reverse("orders"))
        self.assertEqual(res.status_code, 401)

    def test_duplicate_order_returns_400(self):
        self.client.post(reverse("orders"), {"checkout_session_id": self.session.pk})
        res = self.client.post(reverse("orders"), {"checkout_session_id": self.session.pk})
        self.assertEqual(res.status_code, 400)
