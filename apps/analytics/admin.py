from django.contrib import admin
from django.utils.html import format_html
from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_badge",
        "actor_display",
        "product",
        "category",
        "created_at",
    ]
    list_filter = ["event_type", "category", "created_at"]
    search_fields = ["session_id", "user__first_name", "user__last_name", "product__name", "category__name"]
    readonly_fields = ["created_at", "user", "session_id", "event_type", "product", "category", "metadata"]
    ordering = ["-created_at"]

    def actor_display(self, obj):
        if obj.user:
            return f"{obj.user.full_name} ({obj.user.email})"
        return f"Session {obj.session_id[:10]}..."

    actor_display.short_description = "User / Session"

    def event_badge(self, obj):
        colors = {
            "PURCHASE": ("#15803d", "#dcfce7"),
            "CHECKOUT_STARTED": ("#b45309", "#fef3c7"),
            "ADD_TO_CART": ("#1d4ed8", "#dbeafe"),
            "REMOVE_FROM_CART": ("#b91c1c", "#fee2e2"),
            "RECOMMENDATION_CLICK": ("#6d28d9", "#ede9fe"),
            "RECOMMENDATION_VIEW": ("#4338ca", "#e0e7ff"),
            "WHATSAPP_CLICK": ("#047857", "#d1fae5"),
            "INSTAGRAM_CLICK": ("#be185d", "#fce7f3"),
            "PRODUCT_CLICK": ("#0369a1", "#e0f2fe"),
            "PRODUCT_VIEW": ("#475569", "#f1f5f9"),
        }
        color, bg = colors.get(obj.event_type, ("#334155", "#e2e8f0"))
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 8px; border-radius:10px; font-weight:600; font-size:11px;">{}</span>',
            bg, color, obj.get_event_type_display()
        )

    event_badge.short_description = "Event Type"
    event_badge.admin_order_field = "event_type"
