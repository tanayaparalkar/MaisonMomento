from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.catalog.models import Product, Category
from apps.inventory.models import StockAdjustment
from apps.inventory.services import adjust_stock, InsufficientStockError

User = get_user_model()

class InventoryDomainTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test Category", slug="test")
        self.product = Product.objects.create(
            name="Test Product",
            sku="TEST-SKU",
            price=Decimal("100.00"),
            stock=10,
            category=self.category,
        )
        self.admin_user = User.objects.create_superuser(
            "admin", "admin@example.com", "password"
        )
        self.client = Client()

    def test_adjust_stock_increase(self):
        updated_product = adjust_stock(
            product=self.product,
            quantity=5,
            adjustment_type="restock",
            reason="New shipment",
            user=self.admin_user
        )
        self.assertEqual(updated_product.stock, 15)

        adjustment = StockAdjustment.objects.filter(product=self.product).first()
        self.assertIsNotNone(adjustment)
        self.assertEqual(adjustment.quantity, 5)
        self.assertEqual(adjustment.previous_stock, 10)
        self.assertEqual(adjustment.new_stock, 15)
        self.assertEqual(adjustment.adjustment_type, "restock")

    def test_adjust_stock_decrease(self):
        updated_product = adjust_stock(
            product=self.product,
            quantity=-3,
            adjustment_type="damaged",
            reason="Broken bottle",
            user=self.admin_user
        )
        self.assertEqual(updated_product.stock, 7)

        adjustment = StockAdjustment.objects.filter(product=self.product).first()
        self.assertEqual(adjustment.quantity, -3)
        self.assertEqual(adjustment.new_stock, 7)

    def test_prevent_negative_stock(self):
        with self.assertRaises(InsufficientStockError):
            adjust_stock(
                product=self.product,
                quantity=-15,
                adjustment_type="manual_correction",
                reason="Oops",
                user=self.admin_user
            )
        
        # Stock should remain unchanged
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        # No adjustment recorded
        self.assertFalse(StockAdjustment.objects.exists())

    def test_dashboard_adjust_stock_view(self):
        self.client.force_login(self.admin_user)
        url = reverse("dashboard:adjust_stock", args=[self.product.id])
        
        # GET should render form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST should adjust stock and redirect
        response = self.client.post(url, {
            "quantity": "2",
            "adjustment_type": "manual_correction",
            "reason": "Test",
            "next": reverse("dashboard:inventory")
        })
        self.assertRedirects(response, reverse("dashboard:inventory"))
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)

    def test_dashboard_stock_history_view(self):
        self.client.force_login(self.admin_user)
        adjust_stock(self.product, -1, "damaged", "Test", self.admin_user)
        
        url = reverse("dashboard:stock_history", args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "-1")
        self.assertContains(response, "Damaged")

    def test_dashboard_health_and_notifications(self):
        self.client.force_login(self.admin_user)
        url = reverse("dashboard:dashboard")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("health", response.context)
        self.assertIn("notifications", response.context)
        self.assertIn("pending_orders_count", response.context)
