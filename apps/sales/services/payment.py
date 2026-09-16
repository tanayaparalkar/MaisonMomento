"""
apps/sales/services/payment.py
================================
Abstract payment interface — NO external SDK is installed or called here.

This module defines the contract that any future payment provider must satisfy.
To integrate a real gateway (Razorpay, Stripe, Cashfree, etc.):

  1. Create apps/sales/services/providers/razorpay.py  (or similar)
  2. Implement the three functions below using the provider's SDK
  3. Point the setting  PAYMENT_BACKEND = "apps.sales.services.providers.razorpay"
  4. The checkout view calls create_payment() / verify_payment() using the backend
     setting — no changes to checkout logic are required.

Extension points
----------------
- create_payment()   → called immediately after place_order() succeeds
- verify_payment()   → called by the payment webhook / callback URL
- refund_payment()   → called from the admin order detail page
"""


class PaymentResult:
    """
    Lightweight value object returned by payment operations.

    Attributes
    ----------
    success : bool
    provider_reference : str | None
        The gateway's own transaction ID (e.g. Razorpay payment_id).
    raw : dict
        Full raw response from the provider for logging.
    """

    def __init__(self, success: bool, provider_reference=None, raw=None):
        self.success = success
        self.provider_reference = provider_reference
        self.raw = raw or {}


import importlib
from django.conf import settings


def _get_backend():
    backend_path = getattr(settings, "PAYMENT_BACKEND", "apps.sales.services.providers.razorpay")
    return importlib.import_module(backend_path)


def create_payment(order):
    """
    Initiate a payment session for the given Order using the configured backend.
    """
    backend = _get_backend()
    if hasattr(backend, "create_payment"):
        return backend.create_payment(order)
    raise NotImplementedError(f"Backend {backend} does not implement create_payment()")


def verify_payment(order, provider_payload):
    """
    Verify an inbound payment callback from the gateway using the configured backend.
    """
    backend = _get_backend()
    if hasattr(backend, "verify_payment"):
        return backend.verify_payment(order, provider_payload)
    raise NotImplementedError(f"Backend {backend} does not implement verify_payment()")


def refund_payment(order, amount=None):
    """
    Initiate a full or partial refund using the configured backend.
    """
    backend = _get_backend()
    if hasattr(backend, "refund_payment"):
        return backend.refund_payment(order, amount=amount)
    raise NotImplementedError(f"Backend {backend} does not implement refund_payment()")

