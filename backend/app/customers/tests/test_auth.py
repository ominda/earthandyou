from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from customers.models import Customer, EmailVerificationToken
from customers.services import create_verification_token, issue_tokens, verify_email_token

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
VERIFY_URL = "/api/v1/auth/verify-email/"
ME_URL = "/api/v1/auth/me/"
REFRESH_URL = "/api/v1/auth/token/refresh/"


def make_customer(email="test@example.com", password="StrongPass123!", verified=False):
    c = Customer.objects.create_user(email=email, password=password)
    if verified:
        c.is_email_verified = True
        c.save()
    return c


class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_register_returns_201(self):
        response = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 201)

    def test_register_returns_tokens_and_user(self):
        response = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "new@example.com")

    def test_register_creates_verification_token(self):
        self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        customer = Customer.objects.get(email="new@example.com")
        self.assertEqual(customer.verification_tokens.filter(is_used=False).count(), 1)

    def test_register_email_not_verified_by_default(self):
        self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        customer = Customer.objects.get(email="new@example.com")
        self.assertFalse(customer.is_email_verified)

    def test_register_duplicate_email_returns_400(self):
        make_customer()
        response = self.client.post(REGISTER_URL, {
            "email": "test@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_register_password_mismatch_returns_400(self):
        response = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "WrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_register_weak_password_returns_400(self):
        response = self.client.post(REGISTER_URL, {
            "email": "new@example.com",
            "password": "123",
            "password_confirm": "123",
        }, format="json")
        self.assertEqual(response.status_code, 400)


class LoginViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()

    def test_login_returns_200(self):
        response = self.client.post(LOGIN_URL, {
            "email": "test@example.com",
            "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 200)

    def test_login_returns_tokens_and_user(self):
        response = self.client.post(LOGIN_URL, {
            "email": "test@example.com",
            "password": "StrongPass123!",
        }, format="json")
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

    def test_login_wrong_password_returns_400(self):
        response = self.client.post(LOGIN_URL, {
            "email": "test@example.com",
            "password": "WrongPass!",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_login_unknown_email_returns_400(self):
        response = self.client.post(LOGIN_URL, {
            "email": "nobody@example.com",
            "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_login_inactive_customer_returns_400(self):
        self.customer.is_active = False
        self.customer.save()
        response = self.client.post(LOGIN_URL, {
            "email": "test@example.com",
            "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(response.status_code, 400)


class LogoutViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        tokens = issue_tokens(self.customer)
        self.access = tokens["access"]
        self.refresh = tokens["refresh"]

    def test_logout_returns_204(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(LOGOUT_URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 204)

    def test_logout_requires_authentication(self):
        response = self.client.post(LOGOUT_URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_logout_without_refresh_token_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(LOGOUT_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)


class VerifyEmailViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        self.token = create_verification_token(self.customer)

    def test_verify_valid_token_returns_200(self):
        response = self.client.post(VERIFY_URL, {"token": str(self.token.token)}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_verify_marks_email_as_verified(self):
        self.client.post(VERIFY_URL, {"token": str(self.token.token)}, format="json")
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_email_verified)

    def test_verify_token_is_consumed(self):
        self.client.post(VERIFY_URL, {"token": str(self.token.token)}, format="json")
        self.token.refresh_from_db()
        self.assertTrue(self.token.is_used)

    def test_verify_used_token_returns_400(self):
        self.client.post(VERIFY_URL, {"token": str(self.token.token)}, format="json")
        response = self.client.post(VERIFY_URL, {"token": str(self.token.token)}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_verify_expired_token_returns_400(self):
        self.token.expires_at = timezone.now() - timedelta(hours=1)
        self.token.save()
        response = self.client.post(VERIFY_URL, {"token": str(self.token.token)}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_verify_invalid_token_returns_400(self):
        response = self.client.post(VERIFY_URL, {"token": "not-a-real-token"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_verify_missing_token_returns_400(self):
        response = self.client.post(VERIFY_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)


class MeViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer(verified=True)
        tokens = issue_tokens(self.customer)
        self.access = tokens["access"]

    def test_me_returns_200(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 200)

    def test_me_returns_correct_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.get(ME_URL)
        self.assertEqual(response.data["email"], self.customer.email)

    def test_me_does_not_expose_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.get(ME_URL)
        self.assertNotIn("password", response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 401)


class TokenRefreshTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_customer()
        tokens = issue_tokens(self.customer)
        self.refresh = tokens["refresh"]

    def test_refresh_returns_new_access_token(self):
        response = self.client.post(REFRESH_URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
