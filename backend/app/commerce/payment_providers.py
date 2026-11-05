"""
Payment provider abstraction layer.

All payment adapters must subclass BasePaymentProvider and implement:
  - initiate(order)  → dict   (data to send/redirect the customer to the gateway)
  - verify(payload)  → PaymentResult  (parse a webhook/callback payload)

The commerce service layer calls these methods and never imports a concrete
adapter directly — adapters are resolved by name via get_provider().
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class PaymentResult:
    """Normalised result returned by any provider's verify() method."""
    success: bool
    provider_reference: str          # Provider's transaction/reference ID
    amount_usd: Decimal
    raw_response: dict = field(default_factory=dict)
    failure_reason: str = ""


class BasePaymentProvider:
    """
    Abstract base for payment adapters.

    Subclasses must override initiate() and verify().
    The name class attribute is used to resolve the provider by string.
    """

    name: str = ""

    def initiate(self, order) -> dict:
        """
        Begin a payment for the given Order.

        Returns a dict that the API layer passes back to the frontend,
        e.g. {"payment_url": "...", "token": "..."} for a redirect flow,
        or {"client_secret": "..."} for an embedded flow.
        """
        raise NotImplementedError

    def verify(self, payload: dict) -> PaymentResult:
        """
        Parse and verify an incoming webhook or callback payload.

        Returns a PaymentResult. Never raises — failures are expressed
        via PaymentResult.success=False and failure_reason.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, BasePaymentProvider] = {}


def register_provider(provider: BasePaymentProvider) -> None:
    _REGISTRY[provider.name] = provider


def get_provider(name: str) -> BasePaymentProvider:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(f"Unknown payment provider: '{name}'. Registered: {list(_REGISTRY)}")
