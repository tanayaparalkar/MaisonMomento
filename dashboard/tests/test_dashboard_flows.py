from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.catalog.models import Product, Category
from apps.customers.models import Customer
from apps.sales.models import Order, OrderItem
from apps.inventory.models import StockAdjustment
from apps.inventory.services import adjust_stock

User = get_user_model()

class DashboardOperationsTest(TestCase):
    def setUp(self):
        # Create Staff User
        self.staff_user = User.objects.create_user(
            username="admin@maison.com", 
            email="admin@maison.com", 
            password="password",
            is_staff=True,
            is_superuser=True
        )
        
        # Create Normal User
        self.normal_user = User.objects.create_user(
            username="user@domain.com", 
            password="password"
        )
        
        self.client = Client()
        
        # Base Data
        self.category = Category.objects.create(name="Woody Test", slug="woody-test")
        self.product = Product.objects.create(
            name="Test Fragrance", 
            sku="TST-001",
            price=Decimal("150.00"),
            stock=10,
            category=self.category,
            is_active=True
        )
        
        self.customer = Customer.objects.create(
            first_name="John", 
            last_name="Doe", 
            email="john@example.com"
        )
        
        self.order = Order.objects.create(
            order_number="ORD-1234",
            customer=self.customer,
            email="john@example.com",
            total=Decimal("150.00"),
            order_status="pending",
            payment_status="paid"
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price=Decimal("150.00")
        )

    # --- PERMISSIONS ---
    def test_permissions_enforced(self):
        """Ensure non-staff users cannot access dashboard."""
        self.client.login(username="user@domain.com", password="password")
        response = self.client.get(reverse("dashboard:dashboard"))
        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)
        
    # --- PRODUCT MANAGEMENT ---
    def test_product_create(self):
        self.client.login(username="admin@maison.com", password="password")
        data = {
            "name": "New Perfume",
            "brand": "Maison",
            "sku": "NEW-001",
            "category": self.category.id,
            "gender": "unisex",
            "fragrance_family": "woody",
            "concentration": "edp",
            "price": "200.00",
            "description": "A great scent.",
            "is_active": "on",
            # formset required management fields
            "images-TOTAL_FORMS": "0",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(reverse("dashboard:product_create"), data)
        self.assertRedirects(response, reverse("dashboard:products"))
        self.assertTrue(Product.objects.filter(sku="NEW-001").exists())

    def test_product_bulk_actions(self):
        self.client.login(username="admin@maison.com", password="password")
        
        # Test deactivate
        response = self.client.post(reverse("dashboard:products"), {
            "action": "deactivate",
            "selected_products": [self.product.id]
        })
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        
        # Test restock
        response = self.client.post(reverse("dashboard:products"), {
            "action": "restock",
            "selected_products": [self.product.id]
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 20) # initial 10 + 10 bulk restock

    # --- INVENTORY MANAGEMENT ---
    def test_inventory_adjustment(self):
        self.client.login(username="admin@maison.com", password="password")
        
        response = self.client.post(reverse("dashboard:adjust_stock", args=[self.product.id]), {
            "adjustment_type": "decrease",
            "quantity": "5",
            "reason": "Damaged in warehouse"
        })
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        
        # Check audit trail
        adj = StockAdjustment.objects.last()
        self.assertEqual(adj.product, self.product)
        self.assertEqual(adj.quantity, -5)

    # --- ORDER MANAGEMENT ---
    def test_order_list_and_search(self):
        self.client.login(username="admin@maison.com", password="password")
        response = self.client.get(reverse("dashboard:orders") + "?q=ORD-1234")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ORD-1234")
        
    def test_order_transitions(self):
        self.client.login(username="admin@maison.com", password="password")
        
        # Transition Pending -> Confirmed
        response = self.client.post(reverse("dashboard:order_transition", args=[self.order.id]), {
            "target_state": "confirmed"
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "confirmed")
        
        # Transition Confirmed -> Packed
        self.client.post(reverse("dashboard:order_transition", args=[self.order.id]), {
            "target_state": "packed"
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "packed")

        # Invalid transition Packed -> Pending should fail safely
        self.client.post(reverse("dashboard:order_transition", args=[self.order.id]), {
            "target_state": "pending"
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "packed")  # State remains packed

    # --- DASHBOARD METRICS ---
    def test_dashboard_metrics(self):
        self.client.login(username="admin@maison.com", password="password")
        response = self.client.get(reverse("dashboard:dashboard"))
        
        self.assertEqual(response.status_code, 200)
        # Verify today's revenue contains the 150.00 from our setup
        self.assertContains(response, "150")
        # Verify pending orders = 1
        self.assertContains(response, "Pending Orders")

    # --- CSV EXPORT ---
    def test_csv_exports(self):
        self.client.login(username="admin@maison.com", password="password")
        
        # Export Orders
        resp = self.client.get(reverse("dashboard:export_data") + "?type=orders")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertContains(resp, "ORD-1234")
        
        # Export Inventory
        resp = self.client.get(reverse("dashboard:export_data") + "?type=inventory")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TST-001")
