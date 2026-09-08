from django.db import models


class AnalyticsEvent(models.Model):
    EVENT_TYPES = [
        ("PRODUCT_VIEW", "Product View"),
        ("PRODUCT_CLICK", "Product Click"),
        ("ADD_TO_CART", "Add to Cart"),
        ("REMOVE_FROM_CART", "Remove from Cart"),
        ("CHECKOUT_STARTED", "Checkout Started"),
        ("PURCHASE", "Purchase"),
        ("RECOMMENDATION_VIEW", "Recommendation View"),
        ("RECOMMENDATION_CLICK", "Recommendation Click"),
        ("WHATSAPP_CLICK", "WhatsApp Click"),
        ("INSTAGRAM_CLICK", "Instagram Click"),
    ]

    user = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events",
        help_text="Customer profile if authenticated"
    )
    session_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Client session identifier"
    )
    event_type = models.CharField(
        max_length=40,
        choices=EVENT_TYPES,
        db_index=True
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events"
    )
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary telemetry metadata (UTM tags, device info, referrers)"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Analytics Event"
        verbose_name_plural = "Analytics Events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_event_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
