from django.db import models
from django.conf import settings

class Notification(models.Model):
    TARGET_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('system', 'System'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    # Type & Intent
    notification_type = models.CharField(max_length=50, db_index=True)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    
    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    url = models.URLField(max_length=500, null=True, blank=True, help_text="Deep link to related resource")
    
    # Context (Loose coupling alternative to GenericForeignKey)
    related_entity_type = models.CharField(max_length=50, null=True, blank=True)
    related_entity_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Recipient
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Null for global admin/system notifications if target_type is admin"
    )
    
    # State
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration for auto-cleanup")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target_type', 'is_read', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.target_type.upper()}] {self.title} ({self.get_severity_display()})"
