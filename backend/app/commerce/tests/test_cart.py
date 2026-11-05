import datetime
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, GemstoneVariety, Product
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer
from commerce.models import Cart, CartItem
from commerce.services import add_to_cart, remove_from_cart, get_or_create_cart, CartError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def make_product(price=500, listing_status=ListingStatus.ACTIVE, species_code="TST"):
    species, _ = GemstoneSpecies.objects.get_or_create(
        code=species_code,
        defaults={"name": f"TestSpecies-{species_code}", "common_name": "Test"},
    )
    gemstone = PhysicalGemstone.objects.create(
        species=species,
        acquisition_date=datetime.date.today(),
    )
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
    )


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# Service layer tests
# ---------------------------------------------------------------------------

class CartServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()

    def test_get_or_create_cart_creates_on_first_call(self):
        cart = get_or_create_cart(self.customer)
        self.assertIsInstance(cart, Cart)
        self.assertEqual(Cart.objects.filter(customer=self.customer).count(), 1)

    def test_get_or_create_cart_is_idempotent(self):
        get_or_create_cart(self.customer)
        get_or_create_cart(self.customer)
        self.assertEqual(Cart.objects.filter(customer=self.customer).count(), 1)

    def test_add_to_cart_creates_item(self):
        product = make_product()
        item = add_to_cart(self.customer, product.pk)
        self.assertIsInstance(item, CartItem)
        self.assertEqual(item.product, product)

    def test_add_unavailable_product_raises(self):
        product = make_product(listing_status=ListingStatus.UNLISTED)
        with self.assertRaises(CartError):
            add_to_cart(self.customer, product.pk)

    def test_add_nonexistent_product_raises(self):
        with self.assertRaises(CartError):
            add_to_cart(self.customer, 99999)

    def test_add_duplicate_raises(self):
        product = make_product()
        add_to_cart(self.customer, product.pk)
        with self.assertRaises(CartError):
            add_to_cart(self.customer, product.pk)

    def test_add_reserved_product_raises(self):
        product = make_product()
        product.inventory_item.is_reserved = True
        product.inventory_item.save()
        with self.assertRaises(CartError):
            add_to_cart(self.customer, product.pk)

    def test_add_sold_product_raises(self):
        product = make_product()
        product.inventory_item.is_sold = True
        product.inventory_item.save()
        with self.assertRaises(CartError):
            add_to_cart(self.customer, product.pk)

    def test_remove_from_cart(self):
        product = make_product()
        add_to_cart(self.customer, product.pk)
        remove_from_cart(self.customer, product.pk)
        self.assertEqual(CartItem.objects.filter(cart__customer=self.customer).count(), 0)

    def test_remove_nonexistent_item_raises(self):
        get_or_create_cart(self.customer)
        with self.assertRaises(CartError):
            remove_from_cart(self.customer, 99999)

    def test_different_customers_have_separate_carts(self):
        other = make_customer("other@example.com")
        product = make_product()
        add_to_cart(self.customer, product.pk)
        cart_other = get_or_create_cart(other)
        self.assertEqual(cart_other.items.count(), 0)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class CartAPITests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)

    def test_get_cart_returns_empty_cart(self):
        res = self.client.get(reverse("cart"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["item_count"], 0)
        self.assertEqual(res.data["items"], [])

    def test_add_item_returns_201_with_cart(self):
        product = make_product()
        res = self.client.post(reverse("cart-items"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["item_count"], 1)
        self.assertEqual(res.data["items"][0]["product_id"], product.pk)

    def test_add_item_total_usd_calculated(self):
        product = make_product(price=1500)
        res = self.client.post(reverse("cart-items"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(float(res.data["total_usd"]), 1500.0)

    def test_add_unavailable_item_returns_400(self):
        product = make_product(listing_status=ListingStatus.UNLISTED)
        res = self.client.post(reverse("cart-items"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 400)

    def test_add_duplicate_item_returns_400(self):
        product = make_product()
        self.client.post(reverse("cart-items"), {"product_id": product.pk})
        res = self.client.post(reverse("cart-items"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 400)

    def test_add_missing_product_id_returns_400(self):
        res = self.client.post(reverse("cart-items"), {})
        self.assertEqual(res.status_code, 400)

    def test_remove_item_returns_updated_cart(self):
        product = make_product()
        self.client.post(reverse("cart-items"), {"product_id": product.pk})
        res = self.client.delete(reverse("cart-item-detail", args=[product.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["item_count"], 0)

    def test_remove_nonexistent_item_returns_404(self):
        res = self.client.delete(reverse("cart-item-detail", args=[99999]))
        self.assertEqual(res.status_code, 404)

    def test_cart_requires_auth(self):
        res = APIClient().get(reverse("cart"))
        self.assertEqual(res.status_code, 401)

    def test_add_item_requires_auth(self):
        product = make_product()
        res = APIClient().post(reverse("cart-items"), {"product_id": product.pk})
        self.assertEqual(res.status_code, 401)

    def test_multiple_items_in_cart(self):
        p1 = make_product(price=500, species_code="TS1")
        p2 = make_product(price=800, species_code="TS2")
        self.client.post(reverse("cart-items"), {"product_id": p1.pk})
        self.client.post(reverse("cart-items"), {"product_id": p2.pk})
        res = self.client.get(reverse("cart"))
        self.assertEqual(res.data["item_count"], 2)
        self.assertEqual(float(res.data["total_usd"]), 1300.0)
