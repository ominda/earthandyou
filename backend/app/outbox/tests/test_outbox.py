from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings

from outbox.models import NotificationLog
from outbox.services import send_email, retry_failed, MAX_RETRIES


TEMPLATES_OVERRIDE = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]


def _mock_render(template_name, context):
    return f"rendered:{template_name}"


class SendEmailTests(TestCase):
    @patch("outbox.services.render_to_string", side_effect=_mock_render)
    @patch("outbox.services.send_mail")
    def test_send_creates_sent_log(self, mock_send, mock_render):
        log = send_email("user@example.com", "Hello", "order_confirm", {"order_ref": "EAY-001"})
        self.assertEqual(log.status, NotificationLog.Status.SENT)
        self.assertIsNotNone(log.sent_at)
        self.assertEqual(log.retry_count, 0)
        mock_send.assert_called_once()

    @patch("outbox.services.render_to_string", side_effect=_mock_render)
    @patch("outbox.services.send_mail", side_effect=Exception("SMTP error"))
    def test_send_failure_creates_failed_log(self, mock_send, mock_render):
        log = send_email("user@example.com", "Hello", "order_confirm", {})
        self.assertEqual(log.status, NotificationLog.Status.FAILED)
        self.assertEqual(log.retry_count, 1)
        self.assertIn("SMTP error", log.error_message)
        self.assertIsNone(log.sent_at)

    @patch("outbox.services.render_to_string", side_effect=_mock_render)
    @patch("outbox.services.send_mail")
    def test_retry_failed_succeeds(self, mock_send, mock_render):
        log = NotificationLog.objects.create(
            recipient="user@example.com",
            subject="Retry",
            template_name="order_confirm",
            context_json={},
            status=NotificationLog.Status.FAILED,
            retry_count=1,
        )
        retry_failed(log)
        log.refresh_from_db()
        self.assertEqual(log.status, NotificationLog.Status.SENT)

    def test_retry_skipped_if_not_failed(self):
        log = NotificationLog.objects.create(
            recipient="user@example.com",
            subject="Already sent",
            template_name="order_confirm",
            context_json={},
            status=NotificationLog.Status.SENT,
        )
        retry_failed(log)  # should be a no-op
        log.refresh_from_db()
        self.assertEqual(log.status, NotificationLog.Status.SENT)

    def test_retry_skipped_if_max_retries_reached(self):
        log = NotificationLog.objects.create(
            recipient="user@example.com",
            subject="Exhausted",
            template_name="order_confirm",
            context_json={},
            status=NotificationLog.Status.FAILED,
            retry_count=MAX_RETRIES,
        )
        retry_failed(log)
        log.refresh_from_db()
        self.assertEqual(log.retry_count, MAX_RETRIES)  # unchanged
