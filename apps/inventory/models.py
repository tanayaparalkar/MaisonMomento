from django.db import models
from django.conf import settings

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ("increase", "Increase"),
        ("decrease", "Decrease"),
        ("restock", "Restock"),
        ("damaged", "Damaged"),
        ("manual_correction", "Manual Correction"),
    ]

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="stock_adjustments",
        help_text="The product whose stock was adjusted."
    )
    quantity = models.IntegerField(help_text="The delta amount by which the stock changed (positive or negative).")
    previous_stock = models.PositiveIntegerField(help_text="Stock before the adjustment.")
    new_stock = models.PositiveIntegerField(help_text="Stock after the adjustment.")
    adjustment_type = models.CharField(
        max_length=50,
        choices=ADJUSTMENT_TYPES,
        help_text="The nature of the adjustment."
    )
    reason = models.TextField(blank=True, help_text="Explanation or context for this adjustment.")
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_adjustments",
        help_text="The admin user who performed this adjustment (null for automated system events)."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.adjustment_type.upper()} {self.quantity} for {self.product.sku}"
