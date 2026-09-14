from django.contrib import admin
from django.utils.html import format_html
from .models import Interaction


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = (
        "visitor_display",
        "product",
        "event_badge",
        "created_at",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    search_fields = (
        "visitor__session_id",
        "product__name",
    )

    autocomplete_fields = (
        "visitor",
        "product",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    def visitor_display(self, obj):
        return format_html(
            '<span style="font-family: monospace;">{}</span>',
            obj.visitor.session_id[:12],
        )

    visitor_display.short_description = "Visitor"

    def event_badge(self, obj):
        colors = {
            "view": ("#EEE8DC", "#473831"),
            "search": ("#E6F3FF", "#1E3A8A"),
            "wishlist": ("#FCE7F3", "#9D174D"),
            "cart": ("#FEF3C7", "#92400E"),
            "purchase": ("#DCFCE7", "#166534"),
            "recommendation_click": ("#EDE9FE", "#5B21B6"),
        }

        bg, fg = colors.get(obj.event_type, ("#F3F4F6", "#374151"))

        return format_html(
            '<span style="background:{}; color:{}; border:1px solid {}; padding:3px 8px; border-radius:4px; font-weight:600;">{}</span>',
            bg,
            fg,
            fg,
            obj.get_event_type_display(),
        )

    event_badge.short_description = "Event"