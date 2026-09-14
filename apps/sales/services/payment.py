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


def create_payment(order):
    """
    Initiate a payment session for the given Order.

    Parameters
    ----------
    order : sales.Order
        A fully created, totalled Order with order.total set.

    Returns
    -------
    PaymentResult
        Contains checkout_url or session data needed to redirect the customer.

    TODO: Replace this stub with a real provider implementation.
    """
    raise NotImplementedError(
        "Payment provider not configured. "
        "Implement create_payment() in a provider module and set PAYMENT_BACKEND."
    )


def verify_payment(order, provider_payload):
    """
    Verify an inbound payment callback/webhook from the gateway.

    Parameters
    ----------
    order : sales.Order
    provider_payload : dict
        Raw POST body or query params from the gateway callback.

    Returns
    -------
    PaymentResult

    TODO: Replace this stub with signature verification + status check.
    """
    raise NotImplementedError(
        "Payment verification not configured. "
        "Implement verify_payment() in a provider module and set PAYMENT_BACKEND."
    )


def refund_payment(order, amount=None):
    """
    Initiate a full or partial refund for a paid Order.

    Parameters
    ----------
    order : sales.Order
        Must have payment_status == 'paid'.
    amount : Decimal | None
        Amount to refund. Defaults to order.total if None.

    Returns
    -------
    PaymentResult

    TODO: Replace this stub with real refund logic.
    """
    raise NotImplementedError(
        "Refund processing not configured. "
        "Implement refund_payment() in a provider module and set PAYMENT_BACKEND."
    )
