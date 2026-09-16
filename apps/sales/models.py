import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    ORDER_STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("confirmed", "Confirmed"),
        ("packed",    "Packed"),
        ("shipped",   "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded",  "Refunded"),
    ]

    order_number = models.CharField(max_length=36, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Registered customer account (optional for guest orders)"
    )
    customer_name = models.CharField(max_length=255, help_text="Full customer recipient name")
    email = models.EmailField(help_text="Customer notification email")
    phone = models.CharField(max_length=32, help_text="Contact telephone number")
    shipping_address = models.TextField(help_text="Complete physical delivery address")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending", db_index=True)
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="pending", db_index=True)
    notes = models.TextField(blank=True, help_text="Internal notes or customer delivery instructions")
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Razorpay Order ID")
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Razorpay Payment ID")
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True, help_text="Razorpay Payment Signature")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer_name} (₹{self.total:,.2f})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_str = timezone.now().strftime("%Y%m%d")
            random_str = uuid.uuid4().hex[:6].upper()
            self.order_number = f"MM-{date_str}-{random_str}"
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        items_total = sum(item.subtotal for item in self.items.all())
        self.subtotal = items_total
        self.total = max(0, self.subtotal - self.discount + self.shipping_cost)
        self.save(update_fields=["subtotal", "total"])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Unit price at moment of purchase")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, help_text="Line item subtotal (quantity * unit_price)")

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ ₹{self.unit_price:,.2f}"

    def save(self, *args, **kwargs):
        if not self.unit_price and self.product:
            self.unit_price = self.product.effective_price
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Cart(models.Model):
    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart for {self.customer.email}"

    @property
    def total_items(self):
        result = self.items.aggregate(total=models.Sum('quantity'))['total']
        return result if result is not None else 0

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Cart"

    @property
    def line_total(self):
        return self.product.effective_price * self.quantity
