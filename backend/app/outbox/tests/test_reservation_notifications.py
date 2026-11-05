from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from outbox.reservation_notifications import notify_reservation_created, notify_reservation_expired
from outbox.models import NotificationLog

Customer = get_user_model()


def _make_customer(email="buyer@example.com"):
    return Customer.objects.create_user(email=email, password="pass")


class _FakeProduct:
    gemstone_id = "EAY-SAP-2026-000001"
    headline = "Blue Sapphire"


class _FakeReservation:
    def __init__(self, customer):
        self.customer = customer
        self.product = _FakeProduct()
        self.expires_at = timezone.now()


class ReservationNotificationTests(TestCase):
    def setUp(self):
        self.customer = _make_customer()
        self.reservation = _FakeReservation(self.customer)

    @patch("outbox.services.send_mail")
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notify_reservation_created(self, mock_render, mock_send):
        notify_reservation_created(self.reservation)
        mock_send.assert_called_once()
        self.assertIn("EAY-SAP-2026-000001", mock_send.call_args.kwargs["subject"])
        log = NotificationLog.objects.get(template_name="reservation_created")
        self.assertEqual(log.status, NotificationLog.Status.SENT)

    @patch("outbox.services.send_mail")
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notify_reservation_expired(self, mock_render, mock_send):
        notify_reservation_expired(self.reservation)
        mock_send.assert_called_once()
        self.assertIn("EAY-SAP-2026-000001", mock_send.call_args.kwargs["subject"])
        log = NotificationLog.objects.get(template_name="reservation_expired")
        self.assertEqual(log.status, NotificationLog.Status.SENT)

    @patch("outbox.services.send_mail", side_effect=Exception("SMTP down"))
    @patch("outbox.services.render_to_string", return_value="body")
    def test_failure_logged_not_raised(self, mock_render, mock_send):
        notify_reservation_created(self.reservation)
        log = NotificationLog.objects.get(template_name="reservation_created")
        self.assertEqual(log.status, NotificationLog.Status.FAILED)
        self.assertIn("SMTP down", log.error_message)
