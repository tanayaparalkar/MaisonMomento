# Notifications Extension Points

The Internal Notification System for Maison Momento has been designed with an Event-Driven Architecture. Instead of hardcoding Email or SMS API calls directly into the business logic (e.g., inside views or model `save()` methods), the system publishes **domain events**.

This creates a lightweight, decoupled system that is fully prepared for background workers (like Celery or RQ) and third-party integrations (like Twilio, SendGrid, or Webhooks) without requiring any changes to the existing business code.

## The Event Dispatcher
Located in `apps/notifications/events.py`, the `publish_event(event_name, **kwargs)` function is used throughout the codebase to signal that something happened.

Current Events:
- `order.placed`
- `order.status_changed`
- `inventory.low_stock`
- `inventory.out_of_stock`
- `product.archived`
- `product.restored`

## How to Extend for External Providers

Currently, the `NotificationService` subscribes to these events to create internal database records (for the Dashboard and Customer Account). To add external providers, you simply create new subscribers.

### 1. Email Notifications (SendGrid / AWS SES)
To implement email notifications without slowing down the web request, you should integrate a task queue like Celery. 

Create a new file `apps/notifications/tasks.py`:
```python
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_order_email_task(order_id, template_name):
    # Fetch order, render template, send email
    pass
```

Then, in `apps/notifications/services.py`, add a new subscriber or extend the existing one:
```python
from .tasks import send_order_email_task

@subscribe('order.placed')
def trigger_order_email(event_data):
    order = event_data.get('order')
    if order and order.email:
        send_order_email_task.delay(order.id, 'order_confirmation')
```

### 2. SMS / WhatsApp (Twilio)
Similar to Email, SMS notifications should be handled asynchronously.

```python
@subscribe('order.status_changed')
def trigger_shipping_sms(event_data):
    order = event_data.get('order')
    new_status = event_data.get('new_status')
    
    if new_status == 'shipped' and order.shipping_phone:
        # Trigger Celery task to hit Twilio API
        send_sms_task.delay(order.shipping_phone, f"Your order #{order.order_number} has shipped!")
```

### 3. Webhooks (External Inventory / ERP sync)
If Maison Momento integrates with an external ERP (like SAP or Netsuite) in the future, you can push inventory events to them via webhooks.

```python
@subscribe('inventory.out_of_stock')
def trigger_erp_webhook(event_data):
    product = event_data.get('product')
    # Trigger Celery task to POST data to ERP endpoint
    trigger_webhook_task.delay("https://erp.maisonmomento.com/api/stock", {"sku": product.sku, "stock": 0})
```

## Summary
To add *any* new notification channel:
1. Do **not** touch `apps/sales/views.py` or `apps/inventory/services.py`.
2. Do **not** touch the `Order` or `Product` models.
3. Write a Celery task for the external API call.
4. Subscribe to the relevant event in `apps/notifications/services.py` and call `.delay()` on your task.
