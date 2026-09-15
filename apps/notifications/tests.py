from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from apps.notifications.models import Notification
from apps.notifications.events import publish_event
from apps.sales.models import Order
from apps.customers.models import Customer
from apps.catalog.models import Product, Category

User = get_user_model()

class NotificationSystemTests(TestCase):
    def setUp(self):
        # Create test users and related entities
        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        self.customer_user = User.objects.create_user('cust', 'cust@test.com', 'pass')
        self.customer = Customer.objects.create(email='cust@test.com', phone="1234567890")
        
        self.category = Category.objects.create(name="Test Cat", slug="test-cat")
        self.product = Product.objects.create(
            name="Test Product", 
            sku="TST-1", 
            price=Decimal("10.00"), 
            stock=10, 
            category=self.category
        )
        
        self.order = Order.objects.create(
            order_number="ORD-123",
            customer=self.customer,
            email="cust@test.com",
            total=Decimal("100.00"),
            payment_status="pending",
            order_status="pending"
        )

    def test_order_placed_event_creates_notifications(self):
        # Publish order placed event
        publish_event('order.placed', order=self.order)
        
        # Should create 1 admin notification and 1 customer notification
        admin_notif = Notification.objects.filter(target_type='admin').first()
        self.assertIsNotNone(admin_notif)
        self.assertEqual(admin_notif.notification_type, 'order_placed')
        
        cust_notif = Notification.objects.filter(target_type='customer', recipient=self.customer_user).first()
        self.assertIsNotNone(cust_notif)
        self.assertEqual(cust_notif.notification_type, 'order_placed')

    def test_order_status_changed_event(self):
        publish_event('order.status_changed', order=self.order, new_status='shipped')
        
        # Only customer gets shipped notification
        cust_notif = Notification.objects.filter(target_type='customer', notification_type='order_status').first()
        self.assertIsNotNone(cust_notif)
        self.assertIn('shipped', cust_notif.title.lower())
        
        # Test cancelled (both admin and customer get notified)
        publish_event('order.status_changed', order=self.order, new_status='cancelled')
        admin_issue = Notification.objects.filter(target_type='admin', notification_type='order_issue').first()
        self.assertIsNotNone(admin_issue)
        
    def test_inventory_events(self):
        publish_event('inventory.out_of_stock', product=self.product)
        admin_notif = Notification.objects.filter(target_type='admin', notification_type='out_of_stock').first()
        self.assertIsNotNone(admin_notif)
        
        publish_event('inventory.low_stock', product=self.product, stock=2)
        admin_notif_low = Notification.objects.filter(target_type='admin', notification_type='low_stock').first()
        self.assertIsNotNone(admin_notif_low)

    def test_product_archived_restored(self):
        publish_event('product.archived', product=self.product, user=self.admin_user)
        admin_notif = Notification.objects.filter(target_type='admin', notification_type='product_archived').first()
        self.assertIsNotNone(admin_notif)

    def test_admin_notification_center_views(self):
        # Create some notifications
        Notification.objects.create(target_type='admin', title='Test 1', message='msg1', notification_type='test')
        Notification.objects.create(target_type='admin', title='Test 2', message='msg2', notification_type='test')
        
        self.client.force_login(self.admin_user)
        
        # Test list view
        response = self.client.get(reverse('dashboard:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test 1')
        
        # Test mark all read
        response = self.client.post(reverse('dashboard:notification_mark_all_read'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(is_read=False).count(), 0)

    def test_customer_notification_views(self):
        notif = Notification.objects.create(
            target_type='customer', 
            recipient=self.customer_user, 
            title='Cust Notif', 
            message='msg', 
            notification_type='test'
        )
        
        self.client.force_login(self.customer_user)
        
        # Test list view
        response = self.client.get(reverse('customers:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cust Notif')
        
        # Test mark read
        response = self.client.post(reverse('customers:mark_notification_read', args=[notif.pk]))
        self.assertEqual(response.status_code, 302)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
