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

    @property
    def subtotal(self):
        return self.line_total


class Voucher(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage (%)"),
        ("flat", "Flat Amount (₹)"),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique promotional code (e.g. MAISON10, VVIP500)"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short description of the promotional privilege"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default="percentage",
        help_text="Whether discount is percentage or fixed amount"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage value (e.g. 15.00 for 15%) or flat amount in INR (e.g. 500.00)"
    )
    min_cart_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Minimum cart subtotal required to redeem this voucher"
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional cap on discount amount for percentage vouchers"
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text="Start date and time when voucher becomes active"
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date and time (leave blank for no expiry)"
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total allowed redemptions (leave blank for unlimited)"
    )
    used_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of times this voucher has been redeemed"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this voucher can be currently used"
    )
    specific_customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vouchers",
        help_text="Restricts redemption to a specific customer account (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voucher"
        verbose_name_plural = "Vouchers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.get_discount_display()})"

    def clean(self):
        if self.code:
            self.code = self.code.strip().upper()
        super().clean()

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def get_discount_display(self):
        if self.discount_type == "percentage":
            return f"{int(self.discount_value) if self.discount_value % 1 == 0 else self.discount_value}% OFF"
        return f"₹{self.discount_value:,.2f} OFF"

    @property
    def is_expired(self):
        if self.valid_until:
            return timezone.now() > self.valid_until
        return False

    @property
    def is_scheduled(self):
        return timezone.now() < self.valid_from

    @property
    def is_usable(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True

    @property
    def status_label(self):
        if not self.is_active:
            return "Deactivated"
        now = timezone.now()
        if now < self.valid_from:
            return "Scheduled"
        if self.valid_until and now > self.valid_until:
            return "Expired"
        if self.max_uses and self.used_count >= self.max_uses:
            return "Usage Limit Reached"
        return "Active"

    def calculate_discount(self, cart_subtotal, customer=None):
        """
        Validate voucher against cart subtotal and customer, returning (is_valid, discount_amount, message).
        """
        cart_subtotal = Decimal(str(cart_subtotal))
        now = timezone.now()

        if not self.is_active:
            return False, Decimal("0.00"), "This privilege voucher has been deactivated."

        if now < self.valid_from:
            formatted_date = self.valid_from.strftime("%b %d, %Y")
            return False, Decimal("0.00"), f"This voucher will become active on {formatted_date}."

        if self.valid_until and now > self.valid_until:
            return False, Decimal("0.00"), "This privilege voucher has expired."

        if self.max_uses and self.used_count >= self.max_uses:
            return False, Decimal("0.00"), "This voucher's redemption limit has been reached."

        if self.specific_customer and customer:
            if self.specific_customer != customer:
                return False, Decimal("0.00"), "This exclusive voucher is reserved for a specific patron account."
        elif self.specific_customer and not customer:
            return False, Decimal("0.00"), "Please log in to your account to redeem this personalised privilege."

        if cart_subtotal < self.min_cart_value:
            return False, Decimal("0.00"), f"Minimum cart value of ₹{self.min_cart_value:,.2f} required for this voucher."

        if self.discount_type == "percentage":
            discount = (cart_subtotal * (self.discount_value / Decimal("100"))).quantize(Decimal("0.01"))
            if self.max_discount and discount > self.max_discount:
                discount = self.max_discount
        else:
            discount = min(self.discount_value, cart_subtotal).quantize(Decimal("0.01"))

        return True, discount, f"Voucher '{self.code}' applied: {self.get_discount_display()} savings."

    def record_redemption(self):
        Voucher.objects.filter(pk=self.pk).update(used_count=models.F("used_count") + 1)
        self.refresh_from_db(fields=["used_count"])

