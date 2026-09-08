from django.db import models


class UserInteraction(models.Model):
    INTERACTION_TYPES = [
        ("PRODUCT_VIEW", "Product View"),
        ("PRODUCT_CLICK", "Product Click"),
    ]

    user = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interactions",
        help_text="Associated customer account if logged in"
    )
    session_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Anonymous visitor session identifier"
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="interactions"
    )
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.CASCADE,
        related_name="interactions"
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "User Interaction"
        verbose_name_plural = "User Interactions"
        ordering = ["-created_at"]

    def __str__(self):
        actor = self.user.full_name if self.user else f"Session {self.session_id[:8]}"
        return f"{actor} - {self.get_interaction_type_display()} on {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.category_id and self.product and self.product.category:
            self.category = self.product.category
        super().save(*args, **kwargs)
