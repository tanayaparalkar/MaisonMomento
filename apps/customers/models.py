from django.db import models
from django.db.models import Sum, Max


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=32, blank=True)
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
        return f"{self.first_name} {self.last_name}"

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
