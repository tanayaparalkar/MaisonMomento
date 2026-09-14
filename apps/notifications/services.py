from django.urls import reverse
from .models import Notification
from .events import subscribe
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notification(
        target_type, notification_type, title, message, 
        severity='info', recipient=None, url=None, 
        entity_type=None, entity_id=None
    ):
        return Notification.objects.create(
            target_type=target_type,
            notification_type=notification_type,
            title=title,
            message=message,
            severity=severity,
            recipient=recipient,
            url=url,
            related_entity_type=entity_type,
            related_entity_id=entity_id
        )

# =======================================================
# EVENT SUBSCRIBERS
# =======================================================

@subscribe('order.placed')
def on_order_placed(event_data):
    order = event_data.get('order')
    if not order: return
    
    # 1. Admin Notification
    url = reverse('dashboard:order_detail', args=[order.id])
    NotificationService.create_notification(
        target_type='admin',
        notification_type='order_placed',
        severity='success',
        title=f"New Order: #{order.order_number}",
        message=f"{order.customer_name} placed an order for ₹{order.total}.",
        url=url,
        entity_type='Order',
        entity_id=str(order.id)
    )

    # 2. Customer Notification (if registered user)
    if order.customer and order.customer.email:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        customer_user = User.objects.filter(email=order.customer.email).first()
        if customer_user:
            NotificationService.create_notification(
                target_type='customer',
                notification_type='order_placed',
                severity='info',
                recipient=customer_user,
                title="Order Confirmed",
                message=f"Thank you! Your order #{order.order_number} has been received.",
                entity_type='Order',
                entity_id=str(order.id)
            )

@subscribe('order.status_changed')
def on_order_status_changed(event_data):
    order = event_data.get('order')
    new_status = event_data.get('new_status')
    if not order or not new_status: return

    # Only notify customer for significant status changes
    if new_status in ['shipped', 'delivered', 'cancelled', 'refunded']:
        if order.customer and order.customer.email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            customer_user = User.objects.filter(email=order.customer.email).first()
            if customer_user:
                severity = 'success' if new_status in ['shipped', 'delivered'] else 'warning'
                
                msg = f"Your order #{order.order_number} has been {new_status}."
                if new_status == 'shipped' and hasattr(order, 'tracking_reference') and order.tracking_reference:
                    msg += f" Tracking: {order.tracking_reference}"
                    
                NotificationService.create_notification(
                    target_type='customer',
                    notification_type='order_status',
                    severity=severity,
                    recipient=customer_user,
                    title=f"Order {new_status.title()}",
                    message=msg,
                    entity_type='Order',
                    entity_id=str(order.id)
                )

        # For cancelled/refunded, notify admins too
        if new_status in ['cancelled', 'refunded']:
            url = reverse('dashboard:order_detail', args=[order.id])
            NotificationService.create_notification(
                target_type='admin',
                notification_type='order_issue',
                severity='warning',
                title=f"Order {new_status.title()}: #{order.order_number}",
                message=f"Order was marked as {new_status}.",
                url=url,
                entity_type='Order',
                entity_id=str(order.id)
            )

@subscribe('inventory.low_stock')
def on_inventory_low_stock(event_data):
    product = event_data.get('product')
    stock = event_data.get('stock')
    if not product: return
    
    url = reverse('dashboard:inventory')
    NotificationService.create_notification(
        target_type='admin',
        notification_type='low_stock',
        severity='warning',
        title=f"Low Stock Alert: {product.name}",
        message=f"Only {stock} units remaining for {product.sku}.",
        url=url,
        entity_type='Product',
        entity_id=str(product.id)
    )

@subscribe('inventory.out_of_stock')
def on_inventory_out_of_stock(event_data):
    product = event_data.get('product')
    if not product: return
    
    url = reverse('dashboard:inventory')
    NotificationService.create_notification(
        target_type='admin',
        notification_type='out_of_stock',
        severity='error',
        title=f"Out of Stock: {product.name}",
        message=f"Product {product.sku} has reached 0 inventory.",
        url=url,
        entity_type='Product',
        entity_id=str(product.id)
    )

@subscribe('product.archived')
def on_product_archived(event_data):
    product = event_data.get('product')
    user = event_data.get('user')
    if not product: return
    
    admin_name = user.username if user else "System"
    url = reverse('dashboard:products')
    NotificationService.create_notification(
        target_type='admin',
        notification_type='product_archived',
        severity='info',
        title=f"Product Archived: {product.name}",
        message=f"{product.sku} was archived by {admin_name}.",
        url=url,
        entity_type='Product',
        entity_id=str(product.id)
    )

@subscribe('product.restored')
def on_product_restored(event_data):
    product = event_data.get('product')
    user = event_data.get('user')
    if not product: return
    
    admin_name = user.username if user else "System"
    url = reverse('dashboard:products')
    NotificationService.create_notification(
        target_type='admin',
        notification_type='product_restored',
        severity='info',
        title=f"Product Restored: {product.name}",
        message=f"{product.sku} was restored by {admin_name}.",
        url=url,
        entity_type='Product',
        entity_id=str(product.id)
    )
