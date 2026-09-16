"""
apps/sales/services/providers/razorpay.py
==========================================
Razorpay payment provider implementation.

Satisfies the contract defined in apps/sales/services/payment.py:
  - create_payment(order)
  - verify_payment(order, provider_payload)
  - refund_payment(order, amount=None)
"""

import logging
from decimal import Decimal
from django.conf import settings
import razorpay
from razorpay.errors import SignatureVerificationError

from apps.sales.services.payment import PaymentResult
from apps.sales.services.order_state import mark_payment_paid, mark_payment_failed
from apps.sales.services.notifications import send_order_confirmation

logger = logging.getLogger(__name__)


def is_razorpay_configured() -> bool:
    """Return True if Razorpay key ID and secret are present in settings."""
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    return bool(key_id and key_secret)


def get_razorpay_client() -> razorpay.Client:
    """
    Instantiate and return a configured Razorpay Client.
    Raises ValueError if keys are not set.
    """
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise ValueError(
            "Razorpay credentials are missing. "
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env."
        )
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment(order) -> PaymentResult:
    """
    Create a Razorpay Order corresponding to the Maison Momento Order.
    Amount is converted to paise (1 INR = 100 paise).
    """
    if not is_razorpay_configured():
        logger.warning(
            "Razorpay not configured; unable to create gateway order for #%s.",
            order.order_number,
        )
        return PaymentResult(
            success=False,
            raw={"error": "Razorpay credentials not configured"},
        )

    try:
        client = get_razorpay_client()
        # Amount in paise (integer)
        amount_paise = int(round(order.total * Decimal("100")))
        currency = getattr(settings, "RAZORPAY_CURRENCY", "INR")

        razorpay_order_data = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": order.order_number,
            "notes": {
                "order_number": order.order_number,
                "customer_email": order.email,
                "customer_phone": order.phone,
            },
            "payment_capture": 1,
        }

        rzp_order = client.order.create(data=razorpay_order_data)
        rzp_order_id = rzp_order.get("id")

        # Save the Razorpay Order ID on the Order model
        order.razorpay_order_id = rzp_order_id
        order.save(update_fields=["razorpay_order_id", "updated_at"])

        logger.info(
            "Created Razorpay order %s for Order #%s (₹%s)",
            rzp_order_id,
            order.order_number,
            order.total,
        )

        return PaymentResult(
            success=True,
            provider_reference=rzp_order_id,
            raw=rzp_order,
        )

    except Exception as e:
        logger.exception(
            "Error creating Razorpay order for Order #%s: %s",
            order.order_number,
            str(e),
        )
        return PaymentResult(
            success=False,
            raw={"error": str(e)},
        )


def verify_payment(order, provider_payload: dict) -> PaymentResult:
    """
    Verify payment signature from Razorpay checkout response.

    Expected payload:
      {
        "razorpay_payment_id": "pay_...",
        "razorpay_order_id": "order_...",
        "razorpay_signature": "..."
      }
    """
    payment_id = provider_payload.get("razorpay_payment_id")
    rzp_order_id = provider_payload.get("razorpay_order_id")
    signature = provider_payload.get("razorpay_signature")

    if not payment_id or not rzp_order_id or not signature:
        logger.error(
            "Missing verification parameters for Order #%s: %s",
            order.order_number,
            provider_payload,
        )
        if order.payment_status == "pending":
            mark_payment_failed(order)
        return PaymentResult(
            success=False,
            raw={"error": "Missing signature parameters"},
        )

    # Sanity check that the order matches
    if order.razorpay_order_id and order.razorpay_order_id != rzp_order_id:
        logger.error(
            "Razorpay order_id mismatch for #%s: expected %s, received %s",
            order.order_number,
            order.razorpay_order_id,
            rzp_order_id,
        )
        if order.payment_status == "pending":
            mark_payment_failed(order)
        return PaymentResult(
            success=False,
            raw={"error": "Order ID mismatch"},
        )

    try:
        client = get_razorpay_client()
        client.utility.verify_payment_signature({
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })

        # Signature is valid! Persist references & update order state
        order.razorpay_payment_id = payment_id
        order.razorpay_signature = signature
        order.save(update_fields=["razorpay_payment_id", "razorpay_signature", "updated_at"])

        if order.payment_status == "pending":
            mark_payment_paid(order, provider_reference=payment_id)
            send_order_confirmation(order)

        logger.info(
            "Payment verified successfully for Order #%s (payment_id=%s)",
            order.order_number,
            payment_id,
        )

        return PaymentResult(
            success=True,
            provider_reference=payment_id,
            raw=provider_payload,
        )

    except SignatureVerificationError as sve:
        logger.warning(
            "Signature verification failed for Order #%s: %s",
            order.order_number,
            str(sve),
        )
        if order.payment_status == "pending":
            mark_payment_failed(order)
        return PaymentResult(
            success=False,
            raw={"error": "Invalid signature"},
        )
    except Exception as e:
        logger.exception(
            "Unexpected error verifying payment for Order #%s: %s",
            order.order_number,
            str(e),
        )
        if order.payment_status == "pending":
            mark_payment_failed(order)
        return PaymentResult(
            success=False,
            raw={"error": str(e)},
        )


def refund_payment(order, amount=None) -> PaymentResult:
    """
    Issue a full or partial refund via Razorpay for a paid order.
    """
    if not order.razorpay_payment_id:
        logger.error(
            "Cannot refund Order #%s: missing razorpay_payment_id",
            order.order_number,
        )
        return PaymentResult(
            success=False,
            raw={"error": "Order has no associated Razorpay payment ID"},
        )

    try:
        client = get_razorpay_client()
        refund_amount = amount if amount is not None else order.total
        amount_paise = int(round(Decimal(str(refund_amount)) * Decimal("100")))

        refund = client.payment.refund(
            order.razorpay_payment_id,
            {"amount": amount_paise},
        )

        logger.info(
            "Refund initiated for Order #%s: %s (amount: ₹%s)",
            order.order_number,
            refund.get("id"),
            refund_amount,
        )

        return PaymentResult(
            success=True,
            provider_reference=refund.get("id"),
            raw=refund,
        )
    except Exception as e:
        logger.exception(
            "Refund failed for Order #%s: %s",
            order.order_number,
            str(e),
        )
        return PaymentResult(
            success=False,
            raw={"error": str(e)},
        )
