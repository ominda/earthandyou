import datetime
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import ShippingRate
from commerce.services import (
    create_reservation, create_checkout_session, get_shipping_cost, CartError,
)


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


def make_product(species_code="SH1", price=Decimal("1500.00"), value_tier=ValueTier.PREMIUM):
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
        price_usd=price,
        listing_status=ListingStatus.ACTIVE,
        value_tier=value_tier,
        headline="Test Gem",
    )


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# get_shipping_cost service tests
# ---------------------------------------------------------------------------

class GetShippingCostTests(TestCase):

    def test_falls_back_to_default_when_no_db_record(self):
        cost = get_shipping_cost(ValueTier.STANDARD)
        self.assertEqual(cost, Decimal("25.00"))

    def test_falls_back_for_each_tier(self):
        self.assertEqual(get_shipping_cost(ValueTier.PREMIUM), Decimal("35.00"))
        self.assertEqual(get_shipping_cost(ValueTier.LUXURY), Decimal("50.00"))
        self.assertEqual(get_shipping_cost(ValueTier.ULTRA_LUXURY), Decimal("75.00"))

    def test_reads_from_db_when_record_exists(self):
        ShippingRate.objects.create(value_tier=ValueTier.STANDARD, rate_usd=Decimal("30.00"))
        cost = get_shipping_cost(ValueTier.STANDARD)
        self.assertEqual(cost, Decimal("30.00"))

    def test_db_rate_overrides_default(self):
        ShippingRate.objects.create(value_tier=ValueTier.LUXURY, rate_usd=Decimal("99.00"))
        self.assertEqual(get_shipping_cost(ValueTier.LUXURY), Decimal("99.00"))
        # Other tiers still use defaults
        self.assertEqual(get_shipping_cost(ValueTier.STANDARD), Decimal("25.00"))

    def test_unknown_tier_falls_back_to_standard_default(self):
        cost = get_shipping_cost("nonexistent_tier")
        self.assertEqual(cost, Decimal("25.00"))


# ---------------------------------------------------------------------------
# Checkout uses DB shipping rate
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class CheckoutUsesDBShippingRateTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.address = CustomerAddress.objects.create(
            customer=self.customer,
            address_type="shipping",
            recipient_name="Ada Lovelace",
            line1="123 Gem St",
            city="Colombo",
            country="LK",
        )

    def test_checkout_uses_db_rate_when_set(self):
        ShippingRate.objects.create(value_tier=ValueTier.PREMIUM, rate_usd=Decimal("40.00"))
        product = make_product(species_code="SH2", value_tier=ValueTier.PREMIUM)
        reservation = create_reservation(self.customer, product.pk)
        session = create_checkout_session(self.customer, reservation.pk, self.address.pk)
        self.assertEqual(session.shipping_usd, Decimal("40.00"))

    def test_checkout_uses_default_rate_when_no_db_record(self):
        product = make_product(species_code="SH3", value_tier=ValueTier.PREMIUM)
        reservation = create_reservation(self.customer, product.pk)
        session = create_checkout_session(self.customer, reservation.pk, self.address.pk)
        self.assertEqual(session.shipping_usd, Decimal("35.00"))


# ---------------------------------------------------------------------------
# ShippingRate API tests
# ---------------------------------------------------------------------------

class ShippingRateListAPITests(TestCase):

    def test_anyone_can_list_rates(self):
        ShippingRate.objects.create(value_tier=ValueTier.STANDARD, rate_usd=Decimal("25.00"))
        ShippingRate.objects.create(value_tier=ValueTier.LUXURY, rate_usd=Decimal("50.00"))
        res = APIClient().get(reverse("shipping-rates"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_empty_list_when_no_rates_configured(self):
        res = APIClient().get(reverse("shipping-rates"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, [])


class ShippingRateUpdateAPITests(TestCase):

    def setUp(self):
        self.staff = make_customer("staff@example.com", is_staff=True)
        self.customer = make_customer()
        self.staff_client = auth_client(self.staff)
        self.customer_client = auth_client(self.customer)

    def test_staff_can_create_rate(self):
        res = self.staff_client.put(
            reverse("shipping-rate-detail", args=[ValueTier.STANDARD]),
            {"rate_usd": "28.00"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["rate_usd"], "28.00")
        self.assertEqual(res.data["value_tier"], ValueTier.STANDARD)

    def test_staff_can_update_existing_rate(self):
        ShippingRate.objects.create(value_tier=ValueTier.LUXURY, rate_usd=Decimal("50.00"))
        res = self.staff_client.put(
            reverse("shipping-rate-detail", args=[ValueTier.LUXURY]),
            {"rate_usd": "60.00"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["rate_usd"], "60.00")
        self.assertEqual(ShippingRate.objects.get(value_tier=ValueTier.LUXURY).rate_usd, Decimal("60.00"))

    def test_non_staff_cannot_update(self):
        res = self.customer_client.put(
            reverse("shipping-rate-detail", args=[ValueTier.STANDARD]),
            {"rate_usd": "10.00"},
        )
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_cannot_update(self):
        res = APIClient().put(
            reverse("shipping-rate-detail", args=[ValueTier.STANDARD]),
            {"rate_usd": "10.00"},
        )
        self.assertEqual(res.status_code, 401)

    def test_invalid_tier_returns_400(self):
        res = self.staff_client.put(
            reverse("shipping-rate-detail", args=["diamond_tier"]),
            {"rate_usd": "100.00"},
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_rate_usd_returns_400(self):
        res = self.staff_client.put(
            reverse("shipping-rate-detail", args=[ValueTier.STANDARD]),
            {},
        )
        self.assertEqual(res.status_code, 400)

    def test_idempotent_update_or_create(self):
        # Two PUTs for the same tier should not create duplicates
        self.staff_client.put(
            reverse("shipping-rate-detail", args=[ValueTier.PREMIUM]),
            {"rate_usd": "35.00"},
        )
        self.staff_client.put(
            reverse("shipping-rate-detail", args=[ValueTier.PREMIUM]),
            {"rate_usd": "45.00"},
        )
        self.assertEqual(ShippingRate.objects.filter(value_tier=ValueTier.PREMIUM).count(), 1)
        self.assertEqual(
            ShippingRate.objects.get(value_tier=ValueTier.PREMIUM).rate_usd,
            Decimal("45.00"),
        )
