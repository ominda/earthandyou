"""
WEBXPAY payment adapter.

WEBXPAY is a Sri Lankan payment gateway used for international card payments.

Integration flow:
  1. initiate(order) — builds a signed payload and returns the gateway URL
     plus form parameters. The frontend POSTs these to WEBXPAY's hosted page.
  2. verify(payload) — validates the HMAC-SHA256 signature on the return/webhook
     callback and returns a normalised PaymentResult.

Required settings (via environment):
  WEBXPAY_MERCHANT_ID   — issued by WEBXPAY
  WEBXPAY_SECRET_KEY    — HMAC signing secret issued by WEBXPAY
  WEBXPAY_API_URL       — gateway endpoint, e.g. https://payment.webxpay.com/

This module self-registers the adapter on import. Wire the import via
CommerceConfig.ready() so it runs at app startup.
"""

import hashlib
import hmac
from decimal import Decimal

from django.conf import settings

from .payment_providers import BasePaymentProvider, PaymentResult, register_provider


def _get_setting(name: str, default: str = "") -> str:
    return getattr(settings, name, default)


def _sign(secret: str, message: str) -> str:
    """Return a lowercase hex HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_signature(secret: str, order_ref: str, amount: str, currency: str) -> str:
    """
    WEBXPAY signature scheme:
      HMAC-SHA256( secret, "{order_ref}|{amount}|{currency}" )
    """
    message = f"{order_ref}|{amount}|{currency}"
    return _sign(secret, message)


class WebXPayProvider(BasePaymentProvider):
    """
    WEBXPAY hosted-page adapter.

    initiate() returns:
      {
        "payment_url": "https://payment.webxpay.com/",
        "params": { ... }   # POST these fields to payment_url
      }

    The frontend renders a hidden form and auto-submits it, redirecting
    the customer to WEBXPAY's hosted payment page.

    On completion WEBXPAY POSTs back to our webhook endpoint (module 4.7).
    """

    name = "webxpay"
    CURRENCY = "USD"

    def initiate(self, order) -> dict:
        merchant_id = _get_setting("WEBXPAY_MERCHANT_ID")
        secret_key = _get_setting("WEBXPAY_SECRET_KEY")
        api_url = _get_setting("WEBXPAY_API_URL", "https://payment.webxpay.com/")

        if not merchant_id or not secret_key:
            raise ValueError(
                "WEBXPAY_MERCHANT_ID and WEBXPAY_SECRET_KEY must be configured."
            )

        amount_str = f"{order.total_usd:.2f}"
        signature = _build_signature(secret_key, order.order_ref, amount_str, self.CURRENCY)

        params = {
            "merchant_id": merchant_id,
            "order_ref": order.order_ref,
            "amount": amount_str,
            "currency": self.CURRENCY,
            "customer_email": order.customer.email,
            "customer_name": order.shipping_address.get("recipient_name", ""),
            "description": f"Earth&You — {order.gemstone_id}",
            "signature": signature,
        }

        return {
            "payment_url": api_url,
            "params": params,
        }

    def verify(self, payload: dict) -> PaymentResult:
        """
        Validate a WEBXPAY callback/webhook payload.

        Expected payload fields:
          order_ref, amount, currency, status, txn_id, signature

        status == "SUCCESS" indicates a successful payment.
        """
        secret_key = _get_setting("WEBXPAY_SECRET_KEY")

        order_ref = payload.get("order_ref", "")
        amount = payload.get("amount", "")
        currency = payload.get("currency", self.CURRENCY)
        status = payload.get("status", "")
        txn_id = payload.get("txn_id", "")
        received_sig = payload.get("signature", "")

        # Verify signature
        expected_sig = _build_signature(secret_key, order_ref, amount, currency)
        if not hmac.compare_digest(expected_sig, received_sig):
            return PaymentResult(
                success=False,
                provider_reference=txn_id,
                amount_usd=Decimal("0"),
                raw_response=payload,
                failure_reason="Invalid signature",
            )

        success = status.upper() == "SUCCESS"
        try:
            amount_usd = Decimal(amount)
        except Exception:
            amount_usd = Decimal("0")

        return PaymentResult(
            success=success,
            provider_reference=txn_id,
            amount_usd=amount_usd,
            raw_response=payload,
            failure_reason="" if success else f"Payment status: {status}",
        )


# Self-register
register_provider(WebXPayProvider())
