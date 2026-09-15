from django.contrib import admin
from .models import VisitorSession


@admin.register(VisitorSession)
class VisitorSessionAdmin(admin.ModelAdmin):
    list_display = (
        "session_id",
        "user",
        "is_active",
        "created_at",
        "last_seen",
    )

    search_fields = (
        "session_id",
        "user__username",
    )

    readonly_fields = (
        "created_at",
        "last_seen",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    ordering = ("-last_seen",)