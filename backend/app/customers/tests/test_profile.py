from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from customers.models import Customer, CustomerAddress, CustomerProfile


def make_customer(email="test@example.com", password="StrongPass1!"):
    return Customer.objects.create_user(email=email, password=password)


def auth_client(customer):
    client = APIClient()
    response = client.post(reverse("auth-login"), {"email": customer.email, "password": "StrongPass1!"})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


class MePatchTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)

    def test_patch_me_updates_name(self):
        res = self.client.patch(reverse("auth-me"), {"first_name": "Ada", "last_name": "Lovelace"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["first_name"], "Ada")
        self.assertEqual(res.data["last_name"], "Lovelace")

    def test_patch_me_cannot_change_email(self):
        res = self.client.patch(reverse("auth-me"), {"email": "hacker@evil.com"})
        self.assertEqual(res.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "test@example.com")

    def test_patch_me_requires_auth(self):
        res = APIClient().patch(reverse("auth-me"), {"first_name": "X"})
        self.assertEqual(res.status_code, 401)


class ProfileTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)

    def test_get_profile_creates_if_missing(self):
        res = self.client.get(reverse("auth-me-profile"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("phone", res.data)
        self.assertTrue(CustomerProfile.objects.filter(customer=self.customer).exists())

    def test_patch_profile_updates_fields(self):
        res = self.client.patch(reverse("auth-me-profile"), {
            "phone": "+94771234567",
            "newsletter_opt_in": True,
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["phone"], "+94771234567")
        self.assertTrue(res.data["newsletter_opt_in"])

    def test_patch_profile_partial(self):
        self.client.patch(reverse("auth-me-profile"), {"phone": "+94771234567"})
        res = self.client.patch(reverse("auth-me-profile"), {"newsletter_opt_in": True})
        self.assertEqual(res.status_code, 200)
        profile = CustomerProfile.objects.get(customer=self.customer)
        self.assertEqual(profile.phone, "+94771234567")

    def test_profile_requires_auth(self):
        res = APIClient().get(reverse("auth-me-profile"))
        self.assertEqual(res.status_code, 401)


class AddressTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.client = auth_client(self.customer)
        self.address_data = {
            "address_type": "shipping",
            "label": "Home",
            "recipient_name": "Ada Lovelace",
            "phone": "+94771234567",
            "line1": "123 Gem Street",
            "city": "Colombo",
            "country": "LK",
            "is_default": True,
        }

    def test_create_address(self):
        res = self.client.post(reverse("auth-me-addresses"), self.address_data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["city"], "Colombo")
        self.assertTrue(res.data["is_default"])

    def test_list_addresses(self):
        self.client.post(reverse("auth-me-addresses"), self.address_data)
        res = self.client.get(reverse("auth-me-addresses"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_list_only_own_addresses(self):
        other = make_customer("other@example.com")
        other_client = auth_client(other)
        other_client.post(reverse("auth-me-addresses"), {**self.address_data, "city": "Kandy"})
        self.client.post(reverse("auth-me-addresses"), self.address_data)
        res = self.client.get(reverse("auth-me-addresses"))
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["city"], "Colombo")

    def test_get_address_detail(self):
        create_res = self.client.post(reverse("auth-me-addresses"), self.address_data)
        pk = create_res.data["id"]
        res = self.client.get(reverse("auth-me-address-detail", args=[pk]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], pk)

    def test_patch_address(self):
        create_res = self.client.post(reverse("auth-me-addresses"), self.address_data)
        pk = create_res.data["id"]
        res = self.client.patch(reverse("auth-me-address-detail", args=[pk]), {"city": "Galle"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["city"], "Galle")

    def test_delete_address(self):
        create_res = self.client.post(reverse("auth-me-addresses"), self.address_data)
        pk = create_res.data["id"]
        res = self.client.delete(reverse("auth-me-address-detail", args=[pk]))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(CustomerAddress.objects.filter(pk=pk).exists())

    def test_cannot_access_other_customers_address(self):
        other = make_customer("other@example.com")
        other_client = auth_client(other)
        create_res = other_client.post(reverse("auth-me-addresses"), self.address_data)
        pk = create_res.data["id"]
        res = self.client.get(reverse("auth-me-address-detail", args=[pk]))
        self.assertEqual(res.status_code, 404)

    def test_default_address_unsets_previous_default(self):
        res1 = self.client.post(reverse("auth-me-addresses"), self.address_data)
        pk1 = res1.data["id"]
        res2 = self.client.post(reverse("auth-me-addresses"), {**self.address_data, "label": "Office", "is_default": True})
        pk2 = res2.data["id"]
        # First address should no longer be default
        addr1 = CustomerAddress.objects.get(pk=pk1)
        addr2 = CustomerAddress.objects.get(pk=pk2)
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)

    def test_default_flag_independent_per_type(self):
        self.client.post(reverse("auth-me-addresses"), {**self.address_data, "address_type": "shipping", "is_default": True})
        self.client.post(reverse("auth-me-addresses"), {**self.address_data, "address_type": "billing", "is_default": True})
        shipping = CustomerAddress.objects.get(customer=self.customer, address_type="shipping")
        billing = CustomerAddress.objects.get(customer=self.customer, address_type="billing")
        self.assertTrue(shipping.is_default)
        self.assertTrue(billing.is_default)

    def test_addresses_require_auth(self):
        res = APIClient().get(reverse("auth-me-addresses"))
        self.assertEqual(res.status_code, 401)
