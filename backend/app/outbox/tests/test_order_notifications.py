from unittest.mock import patch, call
from django.test import TestCase
from django.contrib.auth import get_user_model

from outbox.order_notifications import (
    notify_order_confirmed,
    notify_order_paid,
    notify_order_dispatched,
    notify_order_delivered,
)

Customer = get_user_model()


def _make_customer(email="buyer@example.com"):
    return Customer.objects.create_user(email=email, password="pass")


class _FakeShipment:
    carrier = "DHL"
    tracking_number = "1Z999"
    tracking_url = "https://track.dhl.com/1Z999"
    estimated_delivery_date = None


class _FakePayment:
    amount_usd = "250.00"
    provider = "webxpay"
    provider_reference = "WXP-001"


class _FakeOrder:
    order_ref = "ORD-2026-000001"
    product_headline = "Blue Sapphire"
    gemstone_id = "EAY-SAP-2026-000001"
    subtotal_usd = "200.00"
    shipping_usd = "25.00"
    total_usd = "225.00"
    shipping_address = {
        "recipient_name": "Jane Doe",
        "line1": "10 Main St",
        "line2": "",
        "city": "Colombo",
        "country": "LK",
    }

    def __init__(self, customer):
        self.customer = customer


class OrderNotificationTests(TestCase):
    def setUp(self):
        self.customer = _make_customer()
        self.order = _FakeOrder(self.customer)

    @patch("outbox.services.send_mail")
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notify_order_confirmed(self, mock_render, mock_send):
        notify_order_confirmed(self.order)
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertIn("ORD-2026-000001", args.kwargs["subject"])

    @patch("outbox.services.send_mail")
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notify_order_paid(self, mock_render, mock_send):
        notify_order_paid(self.order, _FakePayment())
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertIn("ORD-2026-000001", args.kwargs["subject"])

    @patch("outbox.services.send_mail")
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notify_order_dispatched(self, mock_render, mock_send):
        notify_order_dispatched(self.order, _FakeShipment())
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertIn("ORD-2026-000001", args.kwargs["subject"])

    @patch("outbox.services.send_mail")
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notify_order_delivered(self, mock_render, mock_send):
        notify_order_delivered(self.order, _FakeShipment())
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertIn("ORD-2026-000001", args.kwargs["subject"])

    @patch("outbox.services.send_mail", side_effect=Exception("SMTP down"))
    @patch("outbox.services.render_to_string", return_value="body")
    def test_notification_failure_does_not_raise(self, mock_render, mock_send):
        # Should not raise — failures are logged, not propagated
        notify_order_confirmed(self.order)
        from outbox.models import NotificationLog
        log = NotificationLog.objects.get(template_name="order_confirm")
        self.assertEqual(log.status, "failed")
