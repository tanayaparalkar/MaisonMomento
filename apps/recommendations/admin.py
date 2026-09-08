from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import UserInteraction


@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = [
        "actor_display",
        "interaction_type_badge",
        "product",
        "category",
        "created_at",
    ]
    list_filter = ["interaction_type", "category", "created_at"]
    search_fields = ["user__first_name", "user__last_name", "session_id", "product__name", "category__name"]
    autocomplete_fields = ["product", "category", "user"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

    def actor_display(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong> <span style="color:#64748b; font-size:11px;">({})</span>',
                obj.user.full_name,
                obj.user.email
            )
        return format_html('<span style="font-family: monospace; color: #475569;">Session {}</span>', obj.session_id[:12])

    actor_display.short_description = "User / Session"

    def interaction_type_badge(self, obj):
        if obj.interaction_type == "PRODUCT_CLICK":
            return mark_safe(
                '<span style="background: #fdf5e6; color: #7a5416; border: 1px solid #dbc493; padding: 2px 7px; border-radius: 2px; font-weight: 700; font-size: 10px; font-family: Courier Prime, monospace;">CLICK</span>'
            )
        return mark_safe(
            '<span style="background: #eee8dc; color: #473831; border: 1px solid #d0c7b7; padding: 2px 7px; border-radius: 2px; font-weight: 700; font-size: 10px; font-family: Courier Prime, monospace;">VIEW</span>'
        )

    interaction_type_badge.short_description = "Interaction"
    interaction_type_badge.admin_order_field = "interaction_type"
