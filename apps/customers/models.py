from django.conf import settings
from django.db import models
from django.db.models import Sum, Max


class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="customer_profile",
        verbose_name="User Account"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(
        upload_to="customer_avatars/",
        blank=True,
        null=True,
        verbose_name="Profile Picture"
    )
    street_address = models.CharField(max_length=255, blank=True, verbose_name="Street Address")
    apartment = models.CharField(max_length=100, blank=True, verbose_name="Apartment, Suite, Unit")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    state = models.CharField(max_length=100, blank=True, verbose_name="State / Province")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Postal Code")
    country = models.CharField(max_length=100, blank=True, default="India", verbose_name="Country")
    firebase_uid = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Reserved for future Firebase Authentication integration"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        fn = self.full_name
        if fn:
            return fn
        if self.user and self.user.username:
            return self.user.username
        return self.email.split("@")[0]

    @property
    def initials(self):
        fn = self.first_name.strip() if self.first_name else ""
        ln = self.last_name.strip() if self.last_name else ""
        if fn and ln:
            return f"{fn[0]}{ln[0]}".upper()
        if fn:
            return fn[:2].upper()
        if self.user and self.user.username:
            return self.user.username[:2].upper()
        if self.email:
            return self.email[:2].upper()
        return "MM"

    @property
    def formatted_address(self):
        lines = []
        if self.street_address:
            street = self.street_address
            if self.apartment:
                street += f", {self.apartment}"
            lines.append(street)
        city_state = ", ".join(filter(None, [self.city, self.state]))
        if self.postal_code:
            city_state = f"{city_state} {self.postal_code}".strip()
        if city_state:
            lines.append(city_state)
        if self.country:
            lines.append(self.country)
        return "\n".join(lines)

    @property
    def number_of_orders(self):
        return self.orders.count()

    @property
    def total_spent(self):
        total = self.orders.filter(payment_status="paid").aggregate(total=Sum("total"))["total"]
        return total or 0.00

    @property
    def last_order(self):
        return self.orders.order_by("-created_at").first()

class Wishlist(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["customer", "product"], name="unique_customer_wishlist")
        ]

    def __str__(self):
        return f"{self.customer.email} - {self.product.name}"
