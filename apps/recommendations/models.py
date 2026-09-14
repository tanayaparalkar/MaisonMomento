from django.db import models


class Interaction(models.Model):

    EVENT_CHOICES = [
        ("view", "Viewed Product"),
        ("search", "Search"),
        ("wishlist", "Wishlist"),
        ("cart", "Added to Cart"),
        ("purchase", "Purchase"),
        ("recommendation_click", "Recommendation Click"),
    ]

    visitor = models.ForeignKey(
        "tracking.VisitorSession",
        on_delete=models.CASCADE,
        related_name="interactions",
        null=True,
        blank=True,
    )

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="interactions",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES,
        default="view",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    metadata = models.JSONField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "event_type", "created_at"], name="interaction_product_event_idx"),
            models.Index(fields=["visitor", "event_type", "created_at"], name="interaction_visitor_event_idx"),
        ]

    def __str__(self):
        return f"{self.visitor.session_id} • {self.event_type} • {self.product.name}"