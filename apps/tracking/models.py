from django.db import models
from django.conf import settings


class VisitorSession(models.Model):
    """
    Tracks both anonymous and authenticated visitors.
    Used by the recommendation engine.
    """

    session_id = models.CharField(max_length=100, unique=True, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visitor_sessions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        if self.user:
            return f"{self.user.username} ({self.session_id})"
        return f"Anonymous ({self.session_id})"