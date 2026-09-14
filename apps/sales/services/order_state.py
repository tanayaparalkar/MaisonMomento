"""
apps/sales/services/order_state.py
=====================================
Order state machine.

Provides the single canonical place to transition Order statuses.
Future payment providers, admin actions, and fulfilment integrations
call these functions instead of mutating order fields directly.

Valid transitions
-----------------
Payment status:
    pending → paid → refunded
    pending → failed

Order status:
    pending → confirmed → packed → shipped → delivered
                                                     ↘
    Any non-delivered state → cancelled
    delivered + payment=paid → refunded

Extension points
----------------
Shipment tracking:
    Pass a ``tracking_reference`` and ``carrier`` to mark_order_shipped().
    Store on the order (add fields when integrating a carrier API).

Payment gateway webhooks:
    mark_payment_paid() / mark_payment_failed() are the entry points for
    webhook handlers. Add idempotency checks (provider_reference uniqueness)
    before the state mutation.

Email notifications:
    Replace the send_*_notification() stub calls with real email tasks.
    Each transition already calls the correct stub so wiring up real mail
    only requires editing notifications.py.
"""

import logging
from django.core.exceptions import ValidationError

from apps.sales.models import Order
from apps.notifications.events import publish_event

logger = logging.getLogger(__name__)

class InvalidStateTransition(ValidationError):
    """
    Raised when an illegal order state transition is attempted.
    """
    pass

# ---------------------------------------------------------------------------
# Payment transitions
# ---------------------------------------------------------------------------

def mark_payment_paid(order, provider_reference=None):
    if order.payment_status != "pending":
        raise InvalidStateTransition(
            f"Cannot mark as paid: order #{order.order_number} "
            f"is already in payment_status='{order.payment_status}'."
        )

    order.payment_status = "paid"
    order.order_status   = "confirmed"
    order.save(update_fields=["payment_status", "order_status", "updated_at"])

    logger.info(
        "Order #%s marked PAID (provider_ref=%s).",
        order.order_number, provider_reference,
    )
    publish_event('order.status_changed', order=order, new_status='confirmed')


def mark_payment_failed(order):
    if order.payment_status != "pending":
        raise InvalidStateTransition(
            f"Cannot mark as failed: order #{order.order_number} "
            f"is in payment_status='{order.payment_status}'."
        )

    order.payment_status = "failed"
    order.save(update_fields=["payment_status", "updated_at"])
    logger.warning("Order #%s marked FAILED.", order.order_number)

# ---------------------------------------------------------------------------
# Fulfilment transitions
# ---------------------------------------------------------------------------

def mark_order_confirmed(order):
    if order.order_status != "pending":
        raise InvalidStateTransition(
            f"Cannot confirm: order #{order.order_number} "
            f"is in order_status='{order.order_status}'."
        )

    order.order_status = "confirmed"
    order.save(update_fields=["order_status", "updated_at"])
    logger.info("Order #%s marked CONFIRMED.", order.order_number)
    publish_event('order.status_changed', order=order, new_status='confirmed')


def mark_order_packed(order):
    if order.order_status != "confirmed":
        raise InvalidStateTransition(
            f"Cannot mark as packed: order #{order.order_number} "
            f"is in order_status='{order.order_status}'."
        )

    order.order_status = "packed"
    order.save(update_fields=["order_status", "updated_at"])
    logger.info("Order #%s marked PACKED.", order.order_number)
    publish_event('order.status_changed', order=order, new_status='packed')


def mark_order_shipped(order, tracking_reference=None):
    if order.order_status not in ("confirmed", "packed"):
        raise InvalidStateTransition(
            f"Cannot mark as shipped: order #{order.order_number} "
            f"is in order_status='{order.order_status}'."
        )

    order.order_status = "shipped"
    order.save(update_fields=["order_status", "updated_at"])
    logger.info(
        "Order #%s marked SHIPPED (tracking=%s).",
        order.order_number, tracking_reference,
    )
    publish_event('order.status_changed', order=order, new_status='shipped')


def mark_order_delivered(order):
    if order.order_status != "shipped":
        raise InvalidStateTransition(
            f"Cannot mark as delivered: order #{order.order_number} "
            f"is in order_status='{order.order_status}'."
        )

    order.order_status = "delivered"
    order.save(update_fields=["order_status", "updated_at"])
    logger.info("Order #%s marked DELIVERED.", order.order_number)
    publish_event('order.status_changed', order=order, new_status='delivered')


def mark_order_cancelled(order):
    terminal_states = ("delivered", "cancelled", "refunded")
    if order.order_status in terminal_states:
        raise InvalidStateTransition(
            f"Cannot cancel: order #{order.order_number} "
            f"is already in order_status='{order.order_status}'."
        )

    order.order_status = "cancelled"
    order.save(update_fields=["order_status", "updated_at"])
    logger.info("Order #%s marked CANCELLED.", order.order_number)
    publish_event('order.status_changed', order=order, new_status='cancelled')


def mark_order_refunded(order, amount=None):
    if order.payment_status != "paid":
        raise InvalidStateTransition(
            f"Cannot refund: order #{order.order_number} "
            f"is in payment_status='{order.payment_status}'."
        )

    refund_amount          = amount if amount is not None else order.total
    order.payment_status   = "refunded"
    order.order_status     = "refunded"
    order.save(update_fields=["payment_status", "order_status", "updated_at"])

    logger.info(
        "Order #%s marked REFUNDED (₹%s).",
        order.order_number, refund_amount,
    )
    publish_event('order.status_changed', order=order, new_status='refunded', amount=refund_amount)
