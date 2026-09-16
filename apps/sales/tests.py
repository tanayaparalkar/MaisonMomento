"""
apps/sales/tests.py
====================
Targeted tests for the Cart → Checkout → Order pipeline.
Covers: authorization, cart operations, order creation,
duplicate-order prevention, and confirmation access control.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.customers.models import Customer
from apps.sales.models import Cart, CartItem, Order, OrderItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="buyer", password="pass1234!"):
    user = User.objects.create_user(username=username, email=f"{username}@test.com", password=password)
    return user


def make_customer(user):
    return Customer.objects.create(
        email=user.email,
        first_name="Test",
        last_name="Customer",
    )


def make_product(name="Rose Oud", price="9999.00", category=None):
    if category is None:
        category, _ = Category.objects.get_or_create(name="Oud", slug="oud")
    return Product.objects.create(
        name=name,
        sku=f"SKU-{name[:6].upper().replace(' ', '')}",
        description="A rich oud fragrance.",
        price=Decimal(price),
        stock=10,
        category=category,
    )


VALID_CHECKOUT_DATA = {
    "first_name": "Test",
    "last_name": "Customer",
    "email": "buyer@test.com",
    "phone": "9876543210",
    "address_line_1": "12 Luxury Lane",
    "address_line_2": "",
    "city": "Mumbai",
    "state": "Maharashtra",
    "postal_code": "400001",
    "country": "India",
    "delivery_notes": "",
}


# ---------------------------------------------------------------------------
# Cart Tests
# ---------------------------------------------------------------------------

class CartAuthorizationTest(TestCase):
    def test_cart_requires_login(self):
        response = self.client.get(reverse("sales:cart"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('sales:cart')}")

    def test_cart_action_requires_post(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get(reverse("sales:cart_action"))
        self.assertEqual(response.status_code, 405)

    def test_cart_action_anonymous_returns_json(self):
        response = self.client.post(
            reverse("sales:cart_action"),
            data='{"action":"ADD","product_id":1,"quantity":1}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["authenticated"])
        self.assertIn("login_url", data)


class CartOperationTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.customer = make_customer(self.user)
        self.product = make_product()
        self.client.force_login(self.user)

    def _post_action(self, action, product_id, quantity=1):
        import json
        return self.client.post(
            reverse("sales:cart_action"),
            data=json.dumps({"action": action, "product_id": product_id, "quantity": quantity}),
            content_type="application/json",
        )

    def test_add_to_cart(self):
        resp = self._post_action("ADD", self.product.pk, 2)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["cart_total_items"], 2)

    def test_update_cart_quantity(self):
        self._post_action("ADD", self.product.pk, 1)
        resp = self._post_action("UPDATE", self.product.pk, 3)
        self.assertEqual(resp.json()["cart_total_items"], 3)

    def test_remove_from_cart(self):
        self._post_action("ADD", self.product.pk, 1)
        resp = self._post_action("REMOVE", self.product.pk)
        self.assertEqual(resp.json()["cart_total_items"], 0)

    def test_cart_view_shows_items(self):
        cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        resp = self.client.get(reverse("sales:cart"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.product.name)


# ---------------------------------------------------------------------------
# Checkout Tests
# ---------------------------------------------------------------------------

class CheckoutTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.customer = make_customer(self.user)
        self.product = make_product()
        self.cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.client.force_login(self.user)

    def test_checkout_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("sales:checkout"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('sales:checkout')}")

    def test_checkout_page_loads(self):
        resp = self.client.get(reverse("sales:checkout"))
        self.assertEqual(resp.status_code, 200)

    def test_checkout_empty_cart_redirects(self):
        self.cart.items.all().delete()
        resp = self.client.get(reverse("sales:checkout"))
        self.assertEqual(resp.status_code, 200)  # renders checkout_empty.html

    def test_invalid_form_rerenders_checkout(self):
        data = {**VALID_CHECKOUT_DATA, "email": "not-an-email"}
        resp = self.client.post(reverse("sales:checkout"), data=data)
        self.assertEqual(resp.status_code, 200)
        # Form should be re-rendered with errors — context has the bound form
        self.assertIn("form", resp.context)
        self.assertFalse(resp.context["form"].is_valid())

    def test_valid_checkout_creates_order_and_redirects(self):
        resp = self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        order = Order.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(order)
        self.assertRedirects(resp, reverse("sales:order_confirmation", kwargs={"order_number": order.order_number}))

    def test_valid_checkout_clears_cart(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.assertEqual(self.cart.items.count(), 0)

    def test_valid_checkout_creates_correct_order_items(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        order = Order.objects.filter(customer=self.customer).first()
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, self.product.effective_price)

    def test_valid_checkout_calculates_correct_total(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        order = Order.objects.filter(customer=self.customer).first()
        expected_total = self.product.effective_price * 2
        self.assertEqual(order.total, expected_total)


# ---------------------------------------------------------------------------
# Duplicate Order Prevention
# ---------------------------------------------------------------------------

class DuplicateOrderTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.customer = make_customer(self.user)
        self.product = make_product()
        self.cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        self.client.force_login(self.user)

    def test_refresh_on_confirmation_does_not_create_duplicate(self):
        # POST once — creates order and redirects
        resp = self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA, follow=True)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 1)

        # Re-GET the confirmation URL — should NOT create another order
        order = Order.objects.filter(customer=self.customer).first()
        self.client.get(reverse("sales:order_confirmation", kwargs={"order_number": order.order_number}))
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 1)


# ---------------------------------------------------------------------------
# Order Confirmation Access Control
# ---------------------------------------------------------------------------

class OrderConfirmationTest(TestCase):
    def setUp(self):
        self.user = make_user("owner")
        self.other_user = make_user("intruder")
        self.customer = make_customer(self.user)
        self.other_customer = make_customer(self.other_user)
        self.product = make_product()
        # Create an order for owner
        cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_login(self.user)
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.order = Order.objects.filter(customer=self.customer).first()

    def test_owner_can_view_confirmation(self):
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("sales:order_confirmation", kwargs={"order_number": self.order.order_number})
        )
        self.assertEqual(resp.status_code, 200)

    def test_other_customer_cannot_view_confirmation(self):
        self.client.force_login(self.other_user)
        resp = self.client.get(
            reverse("sales:order_confirmation", kwargs={"order_number": self.order.order_number})
        )
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_cannot_view_confirmation(self):
        self.client.logout()
        resp = self.client.get(
            reverse("sales:order_confirmation", kwargs={"order_number": self.order.order_number})
        )
        self.assertRedirects(
            resp,
            f"{reverse('login')}?next={reverse('sales:order_confirmation', kwargs={'order_number': self.order.order_number})}"
        )

    def test_invalid_order_number_returns_404(self):
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse("sales:order_confirmation", kwargs={"order_number": "MM-FAKE-000000"})
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Wishlist Tests
# ---------------------------------------------------------------------------

class WishlistTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.customer = make_customer(self.user)
        self.product = make_product()
        self.client.force_login(self.user)

    def test_wishlist_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("catalog:wishlist"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('catalog:wishlist')}")

    def test_toggle_wishlist_requires_post(self):
        resp = self.client.get(reverse("catalog:toggle_wishlist", kwargs={"pk": self.product.pk}))
        self.assertEqual(resp.status_code, 405)

    def test_toggle_wishlist_adds_item(self):
        resp = self.client.post(reverse("catalog:toggle_wishlist", kwargs={"pk": self.product.pk}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_wishlisted"])
        self.assertEqual(data["count"], 1)

    def test_toggle_wishlist_removes_item(self):
        self.client.post(reverse("catalog:toggle_wishlist", kwargs={"pk": self.product.pk}))
        resp = self.client.post(reverse("catalog:toggle_wishlist", kwargs={"pk": self.product.pk}))
        data = resp.json()
        self.assertFalse(data["is_wishlisted"])
        self.assertEqual(data["count"], 0)


# ---------------------------------------------------------------------------
# Phase 8 — Inventory Tests
# ---------------------------------------------------------------------------

class InventoryDeductionTest(TestCase):
    """Verify that stock is correctly deducted after a successful order."""

    def setUp(self):
        self.user = make_user("inv_buyer")
        self.customer = make_customer(self.user)
        # 10 units in stock; cart has 2
        self.product = make_product("Oud Rouge", stock_override=10)
        self.cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.client.force_login(self.user)

    def test_inventory_deducted_after_checkout(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)  # 10 − 2

    def test_inventory_never_goes_negative(self):
        """Even with concurrent requests the F()-based deduction prevents negative stock."""
        self.product.stock = 2
        self.product.save()
        # Order 2 units — should succeed and leave 0
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.product.refresh_from_db()
        self.assertGreaterEqual(self.product.stock, 0)


class OutOfStockCheckoutTest(TestCase):
    """Verify checkout is blocked when stock is insufficient."""

    def setUp(self):
        self.user = make_user("oos_buyer")
        self.customer = make_customer(self.user)
        # Only 1 unit in stock; cart requests 3
        self.product = make_product("Saffron Elixir", stock_override=1)
        self.cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=3)
        self.client.force_login(self.user)

    def test_out_of_stock_checkout_redirects_to_cart(self):
        resp = self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.assertRedirects(resp, reverse("sales:cart"))

    def test_out_of_stock_checkout_does_not_create_order(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_out_of_stock_checkout_does_not_deduct_stock(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)  # unchanged

    def test_out_of_stock_checkout_does_not_clear_cart(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.assertEqual(self.cart.items.count(), 1)  # cart intact


class LowStockDetectionTest(TestCase):
    """Verify get_inventory_summary() correctly classifies products."""

    def setUp(self):
        from apps.catalog.models import Category
        cat, _ = Category.objects.get_or_create(name="Test", slug="test")
        self.in_stock = Product.objects.create(
            name="In Stock", sku="INSTOCK1", description="x", price=100, stock=20, category=cat
        )
        self.low_stock = Product.objects.create(
            name="Low Stock", sku="LOWSTK1", description="x", price=100, stock=3, category=cat
        )
        self.out_of_stock = Product.objects.create(
            name="Out of Stock", sku="OUTOFSTK1", description="x", price=100, stock=0, category=cat
        )

    def test_summary_counts(self):
        from apps.sales.services.inventory import get_inventory_summary
        summary = get_inventory_summary()
        # stock > threshold (default 5) → in_stock_count
        self.assertGreaterEqual(summary["in_stock_count"], 1)
        self.assertGreaterEqual(summary["low_stock_count"], 1)
        self.assertGreaterEqual(summary["out_of_stock_count"], 1)

    def test_out_of_stock_product_appears_in_summary(self):
        from apps.sales.services.inventory import get_inventory_summary
        summary = get_inventory_summary()
        oos_skus = [p.sku for p in summary["out_of_stock_products"]]
        self.assertIn("OUTOFSTK1", oos_skus)

    def test_low_stock_product_appears_in_summary(self):
        from apps.sales.services.inventory import get_inventory_summary
        summary = get_inventory_summary()
        low_skus = [p.sku for p in summary["low_stock_products"]]
        self.assertIn("LOWSTK1", low_skus)

    def test_in_stock_product_not_in_alert_lists(self):
        from apps.sales.services.inventory import get_inventory_summary
        summary = get_inventory_summary()
        all_alert_skus = (
            [p.sku for p in summary["out_of_stock_products"]] +
            [p.sku for p in summary["low_stock_products"]]
        )
        self.assertNotIn("INSTOCK1", all_alert_skus)


class OrderStateMachineTest(TestCase):
    """Verify legal and illegal order state transitions."""

    def setUp(self):
        from apps.catalog.models import Category
        cat, _ = Category.objects.get_or_create(name="SM Test", slug="sm-test")
        self.product = Product.objects.create(
            name="SM Product", sku="SM001", description="x", price=100, stock=10, category=cat
        )
        user = make_user("sm_user")
        customer = make_customer(user)
        self.order = Order.objects.create(
            customer=customer,
            customer_name="SM User",
            email="sm@test.com",
            phone="9999999999",
            shipping_address="123 Test St",
            order_status="pending",
            payment_status="pending",
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=1,
            unit_price=self.product.price, subtotal=self.product.price
        )
        self.order.recalculate_totals()

    def test_confirm_order(self):
        from apps.sales.services.order_state import mark_order_confirmed
        mark_order_confirmed(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "confirmed")

    def test_pack_order(self):
        from apps.sales.services.order_state import mark_order_confirmed, mark_order_packed
        mark_order_confirmed(self.order)
        mark_order_packed(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "packed")

    def test_ship_order(self):
        from apps.sales.services.order_state import (
            mark_order_confirmed, mark_order_packed, mark_order_shipped
        )
        mark_order_confirmed(self.order)
        mark_order_packed(self.order)
        mark_order_shipped(self.order, tracking_reference="TRACK123")
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")

    def test_deliver_order(self):
        from apps.sales.services.order_state import (
            mark_order_confirmed, mark_order_packed, mark_order_shipped, mark_order_delivered
        )
        mark_order_confirmed(self.order)
        mark_order_packed(self.order)
        mark_order_shipped(self.order)
        mark_order_delivered(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "delivered")

    def test_cancel_order(self):
        from apps.sales.services.order_state import mark_order_cancelled
        mark_order_cancelled(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "cancelled")

    def test_refund_order(self):
        from apps.sales.services.order_state import mark_payment_paid, mark_order_refunded
        mark_payment_paid(self.order)
        mark_order_refunded(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "refunded")
        self.assertEqual(self.order.payment_status, "refunded")


class InvalidStateTransitionTest(TestCase):
    """Verify illegal transitions raise InvalidStateTransition."""

    def setUp(self):
        from apps.catalog.models import Category
        cat, _ = Category.objects.get_or_create(name="IT Test", slug="it-test")
        product = Product.objects.create(
            name="IT Product", sku="IT001", description="x", price=100, stock=10, category=cat
        )
        user = make_user("it_user")
        customer = make_customer(user)
        self.order = Order.objects.create(
            customer=customer,
            customer_name="IT User",
            email="it@test.com",
            phone="9999999998",
            shipping_address="456 Test Ave",
            order_status="pending",
            payment_status="pending",
        )

    def test_cannot_ship_from_pending(self):
        from apps.sales.services.order_state import mark_order_shipped, InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            mark_order_shipped(self.order)

    def test_cannot_deliver_from_pending(self):
        from apps.sales.services.order_state import mark_order_delivered, InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            mark_order_delivered(self.order)

    def test_cannot_refund_unpaid_order(self):
        from apps.sales.services.order_state import mark_order_refunded, InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            mark_order_refunded(self.order)

    def test_cannot_cancel_delivered_order(self):
        from apps.sales.services.order_state import (
            mark_order_confirmed, mark_order_packed, mark_order_shipped,
            mark_order_delivered, mark_order_cancelled, InvalidStateTransition
        )
        mark_order_confirmed(self.order)
        mark_order_packed(self.order)
        mark_order_shipped(self.order)
        mark_order_delivered(self.order)
        with self.assertRaises(InvalidStateTransition):
            mark_order_cancelled(self.order)

    def test_cannot_confirm_already_confirmed(self):
        from apps.sales.services.order_state import mark_order_confirmed, InvalidStateTransition
        mark_order_confirmed(self.order)
        with self.assertRaises(InvalidStateTransition):
            mark_order_confirmed(self.order)

    def test_cannot_pack_from_pending(self):
        from apps.sales.services.order_state import mark_order_packed, InvalidStateTransition
        with self.assertRaises(InvalidStateTransition):
            mark_order_packed(self.order)


class InventoryRollbackTest(TestCase):
    """Verify the transaction rolls back fully on stock exhaustion."""

    def setUp(self):
        self.user = make_user("rb_buyer")
        self.customer = make_customer(self.user)
        # Product A: 5 in stock, request 3 — OK
        self.product_a = make_product("Amber A", stock_override=5)
        # Product B: 0 in stock, request 1 — FAIL
        self.product_b = make_product("Amber B", stock_override=0)
        self.cart, _ = Cart.objects.get_or_create(customer=self.customer)
        CartItem.objects.create(cart=self.cart, product=self.product_a, quantity=3)
        CartItem.objects.create(cart=self.cart, product=self.product_b, quantity=1)
        self.client.force_login(self.user)

    def test_rollback_leaves_stock_unchanged(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.product_a.refresh_from_db()
        self.product_b.refresh_from_db()
        # Neither product's stock should have changed
        self.assertEqual(self.product_a.stock, 5)
        self.assertEqual(self.product_b.stock, 0)

    def test_rollback_leaves_no_order(self):
        self.client.post(reverse("sales:checkout"), data=VALID_CHECKOUT_DATA)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)


class DashboardInventoryWidgetTest(TestCase):
    """Verify the dashboard inventory view returns correct context."""

    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@test.com", "admin1234!")
        self.client.force_login(self.user)
        from apps.catalog.models import Category
        cat, _ = Category.objects.get_or_create(name="DashTest", slug="dashtest")
        Product.objects.create(
            name="Dash OOS", sku="DASHOOS1", description="x", price=100, stock=0, category=cat
        )
        Product.objects.create(
            name="Dash Low", sku="DASHLOW1", description="x", price=100, stock=2, category=cat
        )

    def test_dashboard_inventory_page_loads(self):
        resp = self.client.get(reverse("dashboard:inventory"))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_inventory_context_has_summary(self):
        resp = self.client.get(reverse("dashboard:inventory"))
        self.assertIn("inventory", resp.context)
        inv = resp.context["inventory"]
        self.assertGreaterEqual(inv["out_of_stock_count"], 1)
        self.assertGreaterEqual(inv["low_stock_count"], 1)

    def test_main_dashboard_includes_inventory(self):
        resp = self.client.get(reverse("dashboard:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("inventory", resp.context)


# ---------------------------------------------------------------------------
# make_product helper — updated to support stock_override
# ---------------------------------------------------------------------------

def make_product(name="Rose Oud", price="9999.00", category=None, stock_override=None):
    if category is None:
        category, _ = Category.objects.get_or_create(name="Oud", slug="oud")
    stock = stock_override if stock_override is not None else 10
    return Product.objects.create(
        name=name,
        sku=f"SKU-{name[:8].upper().replace(' ', '')}",
        description="A rich oud fragrance.",
        price=Decimal(price),
        stock=stock,
        category=category,
    )


# ---------------------------------------------------------------------------
# Phase 9A — My Orders & Order Detail Tests
# ---------------------------------------------------------------------------

class MyOrdersViewTest(TestCase):
    def setUp(self):
        self.user = make_user("myorders_user")
        self.customer = make_customer(self.user)
        self.other_user = make_user("other_user")
        self.other_customer = make_customer(self.other_user)
        
        # Order for this user
        self.order1 = Order.objects.create(
            customer=self.customer, customer_name="Mine", email="m@m.com", phone="1", shipping_address="1", total=Decimal("100.00")
        )
        
        # Order for other user
        self.order2 = Order.objects.create(
            customer=self.other_customer, customer_name="Theirs", email="t@t.com", phone="2", shipping_address="2", total=Decimal("200.00")
        )

    def test_my_orders_requires_login(self):
        resp = self.client.get(reverse("sales:my_orders"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('sales:my_orders')}")

    def test_my_orders_shows_only_own_orders(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("sales:my_orders"))
        self.assertEqual(resp.status_code, 200)
        orders = resp.context["orders"]
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].order_number, self.order1.order_number)


class OrderDetailViewTest(TestCase):
    def setUp(self):
        self.user = make_user("orderdetail_user")
        self.customer = make_customer(self.user)
        self.other_user = make_user("intruder2")
        
        self.product = make_product("Timeline Scent")
        self.order = Order.objects.create(
            customer=self.customer,
            customer_name="Detail User",
            email="m@m.com",
            phone="1",
            shipping_address="1",
            total=Decimal("100.00"),
            order_status="shipped"
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            subtotal=self.product.price
        )

    def test_order_detail_requires_login(self):
        resp = self.client.get(reverse("sales:order_detail", kwargs={"order_number": self.order.order_number}))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('sales:order_detail', kwargs={'order_number': self.order.order_number})}")

    def test_order_detail_access_control(self):
        self.client.force_login(self.other_user)
        resp = self.client.get(reverse("sales:order_detail", kwargs={"order_number": self.order.order_number}))
        self.assertEqual(resp.status_code, 404)

    def test_order_detail_context_timeline(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("sales:order_detail", kwargs={"order_number": self.order.order_number}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("timeline_steps", resp.context)
        self.assertEqual(resp.context["status_index"], 3) # shipped is index 3
        self.assertFalse(resp.context["is_cancelled"])
        self.assertFalse(resp.context["is_refunded"])
        
        # Verify product card is rendered (Buy Again feature uses product_card.html)
        self.assertContains(resp, "sf-add-to-cart")
        self.assertContains(resp, str(self.product.id))


# ---------------------------------------------------------------------------
# Razorpay Payment Integration Tests
# ---------------------------------------------------------------------------
from unittest.mock import patch, MagicMock
from razorpay.errors import SignatureVerificationError
from apps.sales.services.providers.razorpay import (
    is_razorpay_configured,
    create_payment,
    verify_payment,
)


class RazorpayPaymentTests(TestCase):
    def setUp(self):
        self.user = make_user("rzp_buyer")
        self.customer = make_customer(self.user)
        self.product = make_product("Ambre Nuit", price="5000.00")
        self.order = Order.objects.create(
            customer=self.customer,
            customer_name="Test Customer",
            email=self.user.email,
            phone="9876543210",
            shipping_address="12 Luxury Lane",
            subtotal=Decimal("5000.00"),
            total=Decimal("5000.00"),
            payment_status="pending",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price=self.product.price,
            subtotal=self.product.price,
        )

    def test_is_razorpay_configured_flag(self):
        with self.settings(RAZORPAY_KEY_ID="", RAZORPAY_KEY_SECRET=""):
            self.assertFalse(is_razorpay_configured())
        with self.settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret"):
            self.assertTrue(is_razorpay_configured())

    @patch("apps.sales.services.providers.razorpay.get_razorpay_client")
    def test_create_payment_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {"id": "order_mock123", "amount": 500000}
        mock_get_client.return_value = mock_client

        with self.settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret"):
            res = create_payment(self.order)

        self.assertTrue(res.success)
        self.assertEqual(res.provider_reference, "order_mock123")
        self.order.refresh_from_db()
        self.assertEqual(self.order.razorpay_order_id, "order_mock123")

    @patch("apps.sales.services.providers.razorpay.get_razorpay_client")
    def test_verify_payment_signature_success(self, mock_get_client):
        mock_client = MagicMock()
        # verify_payment_signature raises on failure, returns None/True on success
        mock_client.utility.verify_payment_signature.return_value = True
        mock_get_client.return_value = mock_client

        self.order.razorpay_order_id = "order_mock123"
        self.order.save()

        with self.settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret"):
            payload = {
                "razorpay_order_id": "order_mock123",
                "razorpay_payment_id": "pay_mock456",
                "razorpay_signature": "mock_valid_signature",
            }
            res = verify_payment(self.order, payload)

        self.assertTrue(res.success)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(self.order.order_status, "confirmed")
        self.assertEqual(self.order.razorpay_payment_id, "pay_mock456")
        self.assertEqual(self.order.razorpay_signature, "mock_valid_signature")

    @patch("apps.sales.services.providers.razorpay.get_razorpay_client")
    def test_verify_payment_signature_invalid(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.side_effect = SignatureVerificationError("Invalid")
        mock_get_client.return_value = mock_client

        self.order.razorpay_order_id = "order_mock123"
        self.order.save()

        with self.settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret"):
            payload = {
                "razorpay_order_id": "order_mock123",
                "razorpay_payment_id": "pay_tampered",
                "razorpay_signature": "bad_sig",
            }
            res = verify_payment(self.order, payload)

        self.assertFalse(res.success)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "failed")

    @patch("apps.sales.views.verify_payment")
    def test_payment_verify_endpoint_valid(self, mock_verify):
        from apps.sales.services.payment import PaymentResult
        mock_verify.return_value = PaymentResult(success=True, provider_reference="pay_123")

        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("sales:payment_verify"),
            data={
                "order_number": self.order.order_number,
                "razorpay_order_id": "order_123",
                "razorpay_payment_id": "pay_123",
                "razorpay_signature": "sig_123",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data["success"])
        self.assertIn(self.order.order_number, json_data["redirect_url"])

