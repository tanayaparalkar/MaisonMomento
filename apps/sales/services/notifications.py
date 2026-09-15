"""
apps/sales/services/notifications.py
======================================
Compatibility shim for notifications. 
Delegates to apps.notifications.events to decouple business logic.
"""

import logging
from apps.notifications.events import publish_event

logger = logging.getLogger(__name__)

def send_order_confirmation(order):
    publish_event('order.placed', order=order)

def send_shipping_notification(order):
    # Backward compatibility, though order_state.py handles this now
    publish_event('order.status_changed', order=order, new_status='shipped')

def send_refund_notification(order, amount):
    # Backward compatibility, though order_state.py handles this now
    publish_event('order.status_changed', order=order, new_status='refunded', amount=amount)
