from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from customers.models import Customer, StaffProfile
from customers.permissions import IsStaff, HasRole


def make_customer(email="customer@example.com", password="StrongPass1!", is_staff=False):
    return Customer.objects.create_user(email=email, password=password, is_staff=is_staff)


def make_staff(email="staff@example.com", role=StaffProfile.Role.CATALOG_MANAGER):
    customer = make_customer(email=email, is_staff=True)
    StaffProfile.objects.create(customer=customer, role=role)
    return customer


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


class StaffMeViewTests(TestCase):

    def test_staff_can_access_me(self):
        staff = make_staff()
        client = auth_client(staff)
        res = client.get(reverse("staff-me"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], staff.email)
        self.assertEqual(res.data["role"], StaffProfile.Role.CATALOG_MANAGER)

    def test_regular_customer_cannot_access_staff_me(self):
        customer = make_customer("regular@example.com")
        client = auth_client(customer)
        res = client.get(reverse("staff-me"))
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_cannot_access_staff_me(self):
        res = APIClient().get(reverse("staff-me"))
        self.assertEqual(res.status_code, 401)

    def test_staff_without_profile_returns_404(self):
        # is_staff=True but no StaffProfile created
        customer = make_customer("noprofile@example.com", is_staff=True)
        client = auth_client(customer)
        res = client.get(reverse("staff-me"))
        self.assertEqual(res.status_code, 404)

    def test_response_includes_mfa_enabled_flag(self):
        staff = make_staff("mfa@example.com")
        client = auth_client(staff)
        res = client.get(reverse("staff-me"))
        self.assertIn("is_mfa_enabled", res.data)
        self.assertFalse(res.data["is_mfa_enabled"])


class IsStaffPermissionTests(TestCase):

    def _make_request(self, user):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user
        return request

    def test_staff_user_passes(self):
        staff = make_customer("s@example.com", is_staff=True)
        perm = IsStaff()
        self.assertTrue(perm.has_permission(self._make_request(staff), None))

    def test_non_staff_fails(self):
        customer = make_customer("c@example.com")
        perm = IsStaff()
        self.assertFalse(perm.has_permission(self._make_request(customer), None))


class HasRolePermissionTests(TestCase):

    def _make_request(self, user):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user
        return request

    def _make_view(self, roles):
        class FakeView:
            required_roles = roles
        return FakeView()

    def test_correct_role_passes(self):
        staff = make_staff("inv@example.com", role=StaffProfile.Role.INVENTORY_MANAGER)
        perm = HasRole()
        view = self._make_view([StaffProfile.Role.INVENTORY_MANAGER])
        self.assertTrue(perm.has_permission(self._make_request(staff), view))

    def test_wrong_role_fails(self):
        staff = make_staff("cat@example.com", role=StaffProfile.Role.CATALOG_MANAGER)
        perm = HasRole()
        view = self._make_view([StaffProfile.Role.INVENTORY_MANAGER])
        self.assertFalse(perm.has_permission(self._make_request(staff), view))

    def test_superadmin_role_passes_when_listed(self):
        staff = make_staff("sup@example.com", role=StaffProfile.Role.SUPERADMIN)
        perm = HasRole()
        view = self._make_view([StaffProfile.Role.SUPERADMIN, StaffProfile.Role.ORDER_MANAGER])
        self.assertTrue(perm.has_permission(self._make_request(staff), view))

    def test_no_required_roles_passes_any_staff(self):
        staff = make_staff("any@example.com", role=StaffProfile.Role.ORDER_MANAGER)
        perm = HasRole()
        view = self._make_view([])
        self.assertTrue(perm.has_permission(self._make_request(staff), view))

    def test_non_staff_fails_regardless_of_role(self):
        customer = make_customer("plain@example.com")
        perm = HasRole()
        view = self._make_view([])
        self.assertFalse(perm.has_permission(self._make_request(customer), view))


class SetupRolesCommandTests(TestCase):

    def test_command_creates_groups(self):
        from django.core.management import call_command
        from django.contrib.auth.models import Group
        call_command("setup_roles", verbosity=0)
        for role in ["inventory_manager", "catalog_manager", "order_manager", "superadmin"]:
            self.assertTrue(Group.objects.filter(name=role).exists())

    def test_command_is_idempotent(self):
        from django.core.management import call_command
        from django.contrib.auth.models import Group
        call_command("setup_roles", verbosity=0)
        call_command("setup_roles", verbosity=0)
        self.assertEqual(Group.objects.filter(name="catalog_manager").count(), 1)
