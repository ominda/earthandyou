import datetime
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer
from commerce.models import Reservation
from commerce.services import create_reservation, release_reservation, expire_stale_reservations, CartError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def make_product(price=500, listing_status=ListingStatus.ACTIVE, species_code="RSV"):
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
    return Product.objects.create(inventory_item=inventory, price_usd=price, listing_status=listing_status)


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------

class ReservationServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()

    def test_create_reservation_marks_inventory_reserved(self):
        product = make_product()
        reservation = create_reservation(self.customer, product.pk)
        product.inventory_item.refresh_from_db()
        self.assertTrue(product.inventory_item.is_reserved)
        self.assertEqual(reservation.status, Reservation.Status.ACTIVE)

    def test_create_reservation_removes_from_cart(self):
        from commerce.services import add_to_cart
        product = make_product(species_code="RC2")
        add_to_cart(self.customer, product.pk)
        create_reservation(self.customer, product.pk)
        from commerce.models import CartItem
        self.assertFalse(CartItem.objects.filter(cart__customer=self.customer, product=product).exists())

    def test_create_reservation_unavailable_product_raises(self):
        product = make_product(listing_status=ListingStatus.UNLISTED)
        with self.assertRaises(CartError):
            create_reservation(self.customer, product.pk)

    def test_create_reservation_already_reserved_raises(self):
        product = make_product(species_code="RC3")
        other = make_customer("other@example.com")
        create_reservation(other, product.pk)
        with self.assertRaises(CartError):
            create_reservation(self.customer, product.pk)

    def test_create_reservation_nonexistent_product_raises(self):
        with self.assertRaises(CartError):
            create_reservation(self.customer, 99999)

    def test_release_reservation_frees_inventory(self):
        product = make_product(species_code="RC4")
        reservation = create_reservation(self.customer, product.pk)
        release_reservation(reservation, actor=self.customer.email)
        reservation.refresh_from_db()
        product.inventory_item.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.RELEASED)
        self.assertFalse(product.inventory_item.is_reserved)

    def test_release_already_released_raises(self):
        product = make_product(species_code="RC5")
        reservation = create_reservation(self.customer, product.pk)
        release_reservation(reservation)
        with self.assertRaises(CartError):
            release_reservation(reservation)

    def test_expire_stale_reservations(self):
        product = make_product(species_code="RC6")
        reservation = create_reservation(self.customer, product.pk)
        # Manually backdate expiry
        Reservation.objects.filter(pk=reservation.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
        count = expire_stale_reservations()
        self.assertEqual(count, 1)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
        product.inventory_item.refresh_from_db()
        self.assertFalse(product.inventory_item.is_reserved)

    def test_expire_stale_skips_non_expired(self):
        product = make_product(species_code="RC7")
        create_reservation(self.customer, product.pk)
        count = expire_stale_reservations()
        self.assertEqual(count, 0)

    def test_is_active_property_false_when_expired(self):
        product = make_product(species_code="RC8")
        reservation = create_reservation(self.customer, product.pk)
        Reservation.objects.filter(pk=reservation.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
        reservation.refresh_from_db()
        self.assertFalse(reservation.is_active)

    def test_is_active_property_true_when_valid(self):
        product = make_product(species_code="RC9")
        reservation = create_reservation(self.customer, product.pk)
        self.assertTrue(reservation.is_active)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class ReservationAPITests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)

    def test_create_reservation_returns_201(self):
        product = make_product(species_code="RA1")
        res = self.client.post(reverse("reservations"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], Reservation.Status.ACTIVE)
        self.assertIn("expires_at", res.data)

    def test_create_reservation_unavailable_returns_400(self):
        product = make_product(listing_status=ListingStatus.UNLISTED, species_code="RA2")
        res = self.client.post(reverse("reservations"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 400)

    def test_create_reservation_missing_product_id_returns_400(self):
        res = self.client.post(reverse("reservations"), {})
        self.assertEqual(res.status_code, 400)

    def test_get_reservation_detail(self):
        product = make_product(species_code="RA3")
        create_res = self.client.post(reverse("reservations"), {"product_id": product.pk})
        pk = create_res.data["id"]
        res = self.client.get(reverse("reservation-detail", args=[pk]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], pk)

    def test_cannot_access_other_customers_reservation(self):
        other = make_customer("other@example.com")
        product = make_product(species_code="RA4")
        reservation = create_reservation(other, product.pk)
        res = self.client.get(reverse("reservation-detail", args=[reservation.pk]))
        self.assertEqual(res.status_code, 404)

    def test_delete_reservation_releases_it(self):
        product = make_product(species_code="RA5")
        create_res = self.client.post(reverse("reservations"), {"product_id": product.pk})
        pk = create_res.data["id"]
        res = self.client.delete(reverse("reservation-detail", args=[pk]))
        self.assertEqual(res.status_code, 204)
        reservation = Reservation.objects.get(pk=pk)
        self.assertEqual(reservation.status, Reservation.Status.RELEASED)

    def test_reservations_require_auth(self):
        res = APIClient().post(reverse("reservations"), {"product_id": 1})
        self.assertEqual(res.status_code, 401)

    def test_expire_reservations_command(self):
        from django.core.management import call_command
        product = make_product(species_code="RA6")
        reservation = create_reservation(self.customer, product.pk)
        Reservation.objects.filter(pk=reservation.pk).update(
            expires_at=timezone.now() - datetime.timedelta(minutes=1)
        )
        call_command("expire_reservations", verbosity=0)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.EXPIRED)
