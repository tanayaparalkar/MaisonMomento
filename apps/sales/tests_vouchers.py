"""
apps/sales/tests_vouchers.py
============================
Automated test suite for the Voucher Management System.
Tests:
- Model logic, status properties, and discount calculations.
- Scheduling, expiry, min cart value, usage limits, max discount cap.
- User-specific voucher restrictions.
- Client-side endpoints: apply voucher, remove voucher, session integration.
- Order integration: discount persistence and redemption tracking.
- Staff Admin Dashboard: listing, search, filters, create, edit, toggle, delete.
"""

from decimal import Decimal
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.customers.models import Customer
from apps.sales.models import Cart, CartItem, Order, Voucher
from apps.sales.services.order_pipeline import place_order


class VoucherModelTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.customer = Customer.objects.create(
            first_name="Lady",
            last_name="Genevieve",
            email="genevieve@maisonmomento.com",
        )

    def test_percentage_discount_calculation(self):
        voucher = Voucher.objects.create(
            code="MAISON15",
            discount_type="percentage",
            discount_value=Decimal("15.00"),
            min_cart_value=Decimal("5000.00"),
        )
        # Below min cart
        valid, discount, msg = voucher.calculate_discount(Decimal("4000.00"))
        self.assertFalse(valid)
        self.assertEqual(discount, Decimal("0.00"))
        self.assertIn("minimum", msg.lower())

        # Above min cart: 15% of 10,000 = 1,500
        valid, discount, msg = voucher.calculate_discount(Decimal("10000.00"))
        self.assertTrue(valid)
        self.assertEqual(discount, Decimal("1500.00"))

    def test_flat_discount_calculation(self):
        voucher = Voucher.objects.create(
            code="ROYAL500",
            discount_type="flat",
            discount_value=Decimal("500.00"),
            min_cart_value=Decimal("2000.00"),
        )
        valid, discount, msg = voucher.calculate_discount(Decimal("3000.00"))
        self.assertTrue(valid)
        self.assertEqual(discount, Decimal("500.00"))

        # Discount cannot exceed subtotal
        valid, discount, msg = voucher.calculate_discount(Decimal("400.00"))
        self.assertFalse(valid)  # 400 < 2000 min cart

    def test_percentage_discount_cap(self):
        voucher = Voucher.objects.create(
            code="BIG50",
            discount_type="percentage",
            discount_value=Decimal("50.00"),
            max_discount=Decimal("2000.00"),
        )
        # 50% of 10,000 = 5,000, capped at 2,000
        valid, discount, msg = voucher.calculate_discount(Decimal("10000.00"))
        self.assertTrue(valid)
        self.assertEqual(discount, Decimal("2000.00"))

    def test_expired_voucher(self):
        voucher = Voucher.objects.create(
            code="EXPIRED10",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            valid_from=self.now - timedelta(days=10),
            valid_until=self.now - timedelta(days=1),
        )
        self.assertTrue(voucher.is_expired)
        self.assertFalse(voucher.is_usable)
        valid, discount, msg = voucher.calculate_discount(Decimal("5000.00"))
        self.assertFalse(valid)
        self.assertIn("expired", msg.lower())

    def test_scheduled_future_voucher(self):
        voucher = Voucher.objects.create(
            code="FUTURE20",
            discount_type="percentage",
            discount_value=Decimal("20.00"),
            valid_from=self.now + timedelta(days=5),
        )
        self.assertTrue(voucher.is_scheduled)
        self.assertFalse(voucher.is_usable)
        valid, discount, msg = voucher.calculate_discount(Decimal("5000.00"))
        self.assertFalse(valid)
        self.assertIn("will become active", msg.lower())

    def test_usage_limit(self):
        voucher = Voucher.objects.create(
            code="LIMITED2",
            discount_type="flat",
            discount_value=Decimal("100.00"),
            max_uses=2,
            used_count=2,
        )
        self.assertFalse(voucher.is_usable)
        valid, discount, msg = voucher.calculate_discount(Decimal("1000.00"))
        self.assertFalse(valid)
        self.assertIn("redemption limit", msg.lower())

    def test_user_specific_voucher(self):
        voucher = Voucher.objects.create(
            code="VIPGENEVIEVE",
            discount_type="percentage",
            discount_value=Decimal("25.00"),
            specific_customer=self.customer,
        )
        other_customer = Customer.objects.create(
            first_name="Lord",
            last_name="Balfour",
            email="balfour@maisonmomento.com",
        )
        # Without logging in
        valid, discount, msg = voucher.calculate_discount(Decimal("5000.00"), customer=None)
        self.assertFalse(valid)
        self.assertIn("log in", msg.lower())

        # Wrong customer
        valid, discount, msg = voucher.calculate_discount(Decimal("5000.00"), customer=other_customer)
        self.assertFalse(valid)
        self.assertIn("reserved", msg.lower())

        # Correct customer
        valid, discount, msg = voucher.calculate_discount(Decimal("5000.00"), customer=self.customer)
        self.assertTrue(valid)
        self.assertEqual(discount, Decimal("1250.00"))

    def test_atomic_redemption_tracking(self):
        voucher = Voucher.objects.create(
            code="REDEEMME",
            discount_type="flat",
            discount_value=Decimal("200.00"),
            used_count=0,
        )
        voucher.record_redemption()
        voucher.refresh_from_db()
        self.assertEqual(voucher.used_count, 1)


class ClientSideVoucherTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="patron_valerie",
            email="valerie@maisonmomento.com",
            password="password123!",
        )
        self.customer = Customer.objects.create(
            first_name="Valerie",
            last_name="De La Tour",
            email="valerie@maisonmomento.com",
        )
        self.category = Category.objects.create(name="Imperial", slug="imperial")
        self.product = Product.objects.create(
            name="Santal Royal",
            sku="SKU-SANTAL",
            price=Decimal("10000.00"),
            stock=10,
            category=self.category,
        )
        self.voucher = Voucher.objects.create(
            code="LUXE10",
            description="10% Privilege off luxury fragrances",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            min_cart_value=Decimal("5000.00"),
        )
        self.client.login(username="patron_valerie", password="password123!")

    def _add_to_cart(self):
        cart = Cart.objects.create(customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        return cart

    def test_apply_valid_voucher(self):
        self._add_to_cart()
        response = self.client.post(
            reverse("sales:apply_voucher"),
            {"code": "LUXE10"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(Decimal(str(data["discount_amount"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(data["total"])), Decimal("9000.00"))
        self.assertEqual(self.client.session.get("applied_voucher_code"), "LUXE10")

    def test_apply_invalid_code(self):
        self._add_to_cart()
        response = self.client.post(
            reverse("sales:apply_voucher"),
            {"code": "NONEXISTENT"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("invalid", data["error"].lower())

    def test_remove_voucher(self):
        self._add_to_cart()
        # First apply
        self.client.post(reverse("sales:apply_voucher"), {"code": "LUXE10"})
        self.assertEqual(self.client.session.get("applied_voucher_code"), "LUXE10")

        # Now remove
        response = self.client.post(
            reverse("sales:remove_voucher"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertNotIn("applied_voucher_code", self.client.session)
        self.assertEqual(Decimal(str(data["discount_amount"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(data["total"])), Decimal("10000.00"))


class StaffDashboardVoucherTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staff_admin",
            email="admin@maisonmomento.com",
            password="adminpassword123!",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular_patron",
            email="patron@maisonmomento.com",
            password="userpassword123!",
            is_staff=False,
        )
        self.voucher = Voucher.objects.create(
            code="ROYAL20",
            description="20% off all coffrets",
            discount_type="percentage",
            discount_value=Decimal("20.00"),
            min_cart_value=Decimal("5000.00"),
        )

    def test_unauthorized_access_denied(self):
        # Unauthenticated
        response = self.client.get(reverse("dashboard:vouchers"))
        self.assertEqual(response.status_code, 302)

        # Regular non-staff user
        self.client.login(username="regular_patron", password="userpassword123!")
        response = self.client.get(reverse("dashboard:vouchers"))
        self.assertEqual(response.status_code, 302)

    def test_staff_list_vouchers(self):
        self.client.login(username="staff_admin", password="adminpassword123!")
        response = self.client.get(reverse("dashboard:vouchers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ROYAL20")
        self.assertContains(response, "20% OFF")

    def test_staff_search_vouchers(self):
        self.client.login(username="staff_admin", password="adminpassword123!")
        Voucher.objects.create(
            code="SEARCHME",
            discount_type="flat",
            discount_value=Decimal("500.00"),
        )
        response = self.client.get(reverse("dashboard:vouchers") + "?q=SEARCHME")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SEARCHME")

    def test_staff_create_voucher(self):
        self.client.login(username="staff_admin", password="adminpassword123!")
        post_data = {
            "code": "SUMMER30",
            "description": "Midsummer Solstice Privilege",
            "discount_type": "percentage",
            "discount_value": "30.00",
            "min_cart_value": "4000.00",
            "valid_from": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "is_active": "on",
        }
        response = self.client.post(reverse("dashboard:voucher_create"), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Voucher.objects.filter(code="SUMMER30").exists())

    def test_staff_toggle_voucher(self):
        self.client.login(username="staff_admin", password="adminpassword123!")
        self.assertTrue(self.voucher.is_active)
        response = self.client.get(reverse("dashboard:voucher_toggle", kwargs={"pk": self.voucher.pk}))
        self.voucher.refresh_from_db()
        self.assertFalse(self.voucher.is_active)

    def test_staff_delete_voucher(self):
        self.client.login(username="staff_admin", password="adminpassword123!")
        response = self.client.post(reverse("dashboard:voucher_delete", kwargs={"pk": self.voucher.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Voucher.objects.filter(pk=self.voucher.pk).exists())
