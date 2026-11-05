from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import NotificationLog

MAX_RETRIES = 3


def send_email(recipient: str, subject: str, template_name: str, context: dict) -> NotificationLog:
    """
    Render `template_name` with `context`, send the email, and persist a NotificationLog.
    Raises nothing — failures are recorded on the log entry and can be retried.
    """
    log = NotificationLog.objects.create(
        recipient=recipient,
        subject=subject,
        template_name=template_name,
        context_json=context,
    )
    _attempt_send(log, context)
    return log


def retry_failed(log: NotificationLog) -> None:
    """Re-attempt delivery for a failed NotificationLog entry."""
    if log.status != NotificationLog.Status.FAILED:
        return
    if log.retry_count >= MAX_RETRIES:
        return
    _attempt_send(log, log.context_json)


def _attempt_send(log: NotificationLog, context: dict) -> None:
    try:
        html_body = render_to_string(f"outbox/{log.template_name}.html", context)
        text_body = render_to_string(f"outbox/{log.template_name}.txt", context)
        send_mail(
            subject=log.subject,
            message=text_body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[log.recipient],
            html_message=html_body,
            fail_silently=False,
        )
        log.status = NotificationLog.Status.SENT
        log.sent_at = timezone.now()
        log.error_message = ""
    except Exception as exc:
        log.retry_count += 1
        log.status = NotificationLog.Status.FAILED
        log.error_message = str(exc)
    finally:
        log.save(update_fields=["status", "sent_at", "retry_count", "error_message"])
