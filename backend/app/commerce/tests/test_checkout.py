import datetime
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Reservation, CheckoutSession
from commerce.services import create_reservation, create_checkout_session, get_shipping_cost, CartError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def make_product(price=1000, listing_status=ListingStatus.ACTIVE, species_code="CHK", value_tier=ValueTier.STANDARD):
    species, _ = GemstoneSpecies.objects.get_or_create(
        code=species_code,
        defaults={"name": f"Species-{species_code}", "common_name": "Test"},
    )
    gemstone = PhysicalGemstone.objects.create(species=species, acquisition_date=datetime.date.today())
    inventory = InventoryItem.objects.create(
        physical_gemstone=gemstone,
        listing_status=listing_status,
        is_reserved=False,
        is_sold=False,
    )
    return Product.objects.create(
        inventory_item=inventory,
        price_usd=price,
        listing_status=listing_status,
        value_tier=value_tier,
    )


def make_address(customer, address_type="shipping", label="Home"):
    return CustomerAddress.objects.create(
        customer=customer,
        address_type=address_type,
        label=label,
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


# ---------------------------------------------------------------------------
# Shipping cost tests
# ---------------------------------------------------------------------------

class ShippingCostTests(TestCase):

    def test_standard_tier_rate(self):
        self.assertEqual(get_shipping_cost(ValueTier.STANDARD), Decimal("25.00"))

    def test_premium_tier_rate(self):
        self.assertEqual(get_shipping_cost(ValueTier.PREMIUM), Decimal("35.00"))

    def test_luxury_tier_rate(self):
        self.assertEqual(get_shipping_cost(ValueTier.LUXURY), Decimal("50.00"))

    def test_ultra_luxury_tier_rate(self):
        self.assertEqual(get_shipping_cost(ValueTier.ULTRA_LUXURY), Decimal("75.00"))


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------

class CheckoutServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.product = make_product(price=1000, species_code="CS1")
        self.reservation = create_reservation(self.customer, self.product.pk)
        self.shipping_addr = make_address(self.customer, "shipping")
        self.billing_addr = make_address(self.customer, "billing")

    def test_create_checkout_session(self):
        session = create_checkout_session(
            self.customer, self.reservation.pk, self.shipping_addr.pk
        )
        self.assertEqual(session.status, CheckoutSession.Status.PENDING)
        self.assertEqual(session.subtotal_usd, Decimal("1000.00"))
        self.assertEqual(session.shipping_usd, Decimal("25.00"))
        self.assertEqual(session.total_usd, Decimal("1025.00"))

    def test_billing_defaults_to_shipping(self):
        session = create_checkout_session(
            self.customer, self.reservation.pk, self.shipping_addr.pk
        )
        self.assertEqual(session.billing_address["id"], self.shipping_addr.pk)
        self.assertEqual(session.shipping_address["id"], self.shipping_addr.pk)

    def test_explicit_billing_address(self):
        session = create_checkout_session(
            self.customer, self.reservation.pk,
            self.shipping_addr.pk, self.billing_addr.pk,
        )
        self.assertEqual(session.billing_address["id"], self.billing_addr.pk)

    def test_address_is_snapshotted(self):
        session = create_checkout_session(
            self.customer, self.reservation.pk, self.shipping_addr.pk
        )
        self.shipping_addr.city = "Kandy"
        self.shipping_addr.save()
        session.refresh_from_db()
        self.assertEqual(session.shipping_address["city"], "Colombo")

    def test_expired_reservation_raises(self):
        Reservation.objects.filter(pk=self.reservation.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
        self.reservation.refresh_from_db()
        with self.assertRaises(CartError):
            create_checkout_session(
                self.customer, self.reservation.pk, self.shipping_addr.pk
            )

    def test_duplicate_checkout_session_raises(self):
        create_checkout_session(self.customer, self.reservation.pk, self.shipping_addr.pk)
        with self.assertRaises(CartError):
            create_checkout_session(self.customer, self.reservation.pk, self.shipping_addr.pk)

    def test_invalid_reservation_raises(self):
        with self.assertRaises(CartError):
            create_checkout_session(self.customer, 99999, self.shipping_addr.pk)

    def test_invalid_shipping_address_raises(self):
        with self.assertRaises(CartError):
            create_checkout_session(self.customer, self.reservation.pk, 99999)

    def test_other_customers_address_raises(self):
        other = make_customer("other@example.com")
        other_addr = make_address(other)
        with self.assertRaises(CartError):
            create_checkout_session(self.customer, self.reservation.pk, other_addr.pk)

    def test_shipping_cost_reflects_value_tier(self):
        luxury_product = make_product(price=5000, species_code="CS2", value_tier=ValueTier.LUXURY)
        reservation = create_reservation(self.customer, luxury_product.pk)
        session = create_checkout_session(self.customer, reservation.pk, self.shipping_addr.pk)
        self.assertEqual(session.shipping_usd, Decimal("50.00"))
        self.assertEqual(session.total_usd, Decimal("5050.00"))

    def test_is_active_property(self):
        session = create_checkout_session(
            self.customer, self.reservation.pk, self.shipping_addr.pk
        )
        self.assertTrue(session.is_active)

    def test_is_active_false_when_expired(self):
        session = create_checkout_session(
            self.customer, self.reservation.pk, self.shipping_addr.pk
        )
        CheckoutSession.objects.filter(pk=session.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
        session.refresh_from_db()
        self.assertFalse(session.is_active)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class CheckoutAPITests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)
        self.product = make_product(species_code="CA1")
        self.reservation = create_reservation(self.customer, self.product.pk)
        self.shipping_addr = make_address(self.customer)

    def test_create_checkout_returns_201(self):
        res = self.client.post(reverse("checkout"), {
            "reservation_id": self.reservation.pk,
            "shipping_address_id": self.shipping_addr.pk,
        })
        self.assertEqual(res.status_code, 201)
        self.assertIn("total_usd", res.data)
        self.assertIn("shipping_address", res.data)

    def test_create_checkout_missing_fields_returns_400(self):
        res = self.client.post(reverse("checkout"), {"reservation_id": self.reservation.pk})
        self.assertEqual(res.status_code, 400)

    def test_create_checkout_invalid_reservation_returns_400(self):
        res = self.client.post(reverse("checkout"), {
            "reservation_id": 99999,
            "shipping_address_id": self.shipping_addr.pk,
        })
        self.assertEqual(res.status_code, 400)

    def test_get_checkout_detail(self):
        create_res = self.client.post(reverse("checkout"), {
            "reservation_id": self.reservation.pk,
            "shipping_address_id": self.shipping_addr.pk,
        })
        pk = create_res.data["id"]
        res = self.client.get(reverse("checkout-detail", args=[pk]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], pk)

    def test_cannot_access_other_customers_checkout(self):
        other = make_customer("other@example.com")
        other_product = make_product(species_code="CA2")
        other_reservation = create_reservation(other, other_product.pk)
        other_addr = make_address(other)
        session = create_checkout_session(other, other_reservation.pk, other_addr.pk)
        res = self.client.get(reverse("checkout-detail", args=[session.pk]))
        self.assertEqual(res.status_code, 404)

    def test_checkout_requires_auth(self):
        res = APIClient().post(reverse("checkout"), {})
        self.assertEqual(res.status_code, 401)
