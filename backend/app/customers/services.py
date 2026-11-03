from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer, EmailVerificationToken


def issue_tokens(customer: Customer) -> dict:
    """Issue a JWT access/refresh token pair for the given customer."""
    refresh = RefreshToken.for_user(customer)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def create_verification_token(customer: Customer) -> EmailVerificationToken:
    """
    Invalidate any existing unused tokens for this customer and issue a new one.
    """
    customer.verification_tokens.filter(is_used=False).update(is_used=True)
    expiry_hours = getattr(settings, "EMAIL_VERIFICATION_EXPIRY_HOURS", 24)
    return EmailVerificationToken.objects.create(
        customer=customer,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
    )


def verify_email_token(token_value: str) -> Customer | None:
    """
    Validate the token and mark the customer's email as verified.
    Returns the customer on success, None on failure.
    """
    try:
        token = EmailVerificationToken.objects.select_related("customer").get(
            token=token_value
        )
    except (EmailVerificationToken.DoesNotExist, ValueError, ValidationError):
        return None

    if not token.is_valid:
        return None

    token.is_used = True
    token.save(update_fields=["is_used"])

    token.customer.is_email_verified = True
    token.customer.save(update_fields=["is_email_verified", "updated_at"])

    return token.customer
