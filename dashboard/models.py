import re
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


def validate_phone_number(value):
    """
    Validates that a phone number contains valid characters and a reasonable digit length.
    Accepts international formatting (+, spaces, hyphens, parentheses).
    """
    if not value:
        return
    digits = re.sub(r"\D", "", value)
    if len(digits) < 7 or len(digits) > 17:
        raise ValidationError("Please enter a valid phone number with 7 to 17 digits.")


class BusinessSettings(models.Model):
    """
    Singleton model holding the centralized public business and contact information
    for Maison Moménto. Only one record is allowed to exist in the database.
    """
    # Business Identity
    business_name = models.CharField(
        max_length=255,
        default="Maison Moménto",
        verbose_name="Business Name",
        help_text="Official name of the luxury maison."
    )

    # Contact Channels
    business_email = models.EmailField(
        max_length=255,
        default="concierge@maisonmomento.com",
        verbose_name="Business Email",
        help_text="Primary email for client concierge inquiries."
    )
    primary_phone = models.CharField(
        max_length=50,
        default="+33 1 40 20 50 50",
        validators=[validate_phone_number],
        verbose_name="Primary Phone Number",
        help_text="Main telephone number for the boutique."
    )
    secondary_phone = models.CharField(
        max_length=50,
        blank=True,
        default="",
        validators=[validate_phone_number],
        verbose_name="Secondary Phone Number (optional)",
        help_text="Optional secondary contact or helpline."
    )
    whatsapp_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        validators=[validate_phone_number],
        verbose_name="WhatsApp Number (optional)",
        help_text="Optional WhatsApp concierge number (with country code)."
    )

    # Social Media
    instagram_url = models.URLField(
        max_length=500,
        blank=True,
        default="https://instagram.com/maisonmomento",
        verbose_name="Instagram URL",
        help_text="Official Instagram profile link."
    )
    facebook_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Facebook URL (optional)",
        help_text="Official Facebook page link."
    )
    linkedin_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="LinkedIn URL (optional)",
        help_text="Official LinkedIn company page link."
    )
    twitter_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="X / Twitter URL (optional)",
        help_text="Official X / Twitter profile link (not displayed by default)."
    )

    # Flagship Boutique & Address
    business_address = models.TextField(
        default="15 Rue de la Paix\n75002 Paris\nFrance",
        verbose_name="Business Address",
        help_text="Physical boutique address displayed on the storefront."
    )
    google_maps_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Google Maps URL (optional)",
        help_text="Direct link to the boutique location on Google Maps."
    )

    # Operating Hours
    business_hours = models.TextField(
        default="Monday – Friday: 10:00 AM – 7:00 PM (CET)\nSaturday: 11:00 AM – 5:00 PM (CET)\nSunday: Closed",
        verbose_name="Business Hours",
        help_text="Opening and concierge availability hours."
    )

    # Metadata
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = "Business Contact Setting"
        verbose_name_plural = "Business Contact Settings"

    def __str__(self):
        return f"{self.business_name} - Contact Information"

    def save(self, *args, **kwargs):
        """
        Enforce singleton constraint: primary key is always 1.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Prevent deletion of the singleton business settings record.
        """
        pass

    @classmethod
    def get_settings(cls):
        """
        Retrieve or create the singleton instance.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def primary_phone_tel(self):
        """
        Normalized telephone number suitable for tel: URI.
        """
        if not self.primary_phone:
            return ""
        # Keep leading + if present, and all digits
        has_plus = self.primary_phone.strip().startswith("+")
        digits = re.sub(r"\D", "", self.primary_phone)
        return f"+{digits}" if has_plus else digits

    @property
    def secondary_phone_tel(self):
        """
        Normalized secondary telephone number suitable for tel: URI.
        """
        if not self.secondary_phone:
            return ""
        has_plus = self.secondary_phone.strip().startswith("+")
        digits = re.sub(r"\D", "", self.secondary_phone)
        return f"+{digits}" if has_plus else digits

    @property
    def whatsapp_url(self):
        """
        Direct WhatsApp click-to-chat URL.
        """
        if not self.whatsapp_number:
            return ""
        digits = re.sub(r"\D", "", self.whatsapp_number)
        return f"https://wa.me/{digits}" if digits else ""


class AdminProfile(models.Model):
    """
    Profile extension for Maison Moménto administrators and staff members.
    Holds display titles, avatars, contact phone, and workspace preferences.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_profile",
        verbose_name="User Account"
    )
    avatar = models.ImageField(
        upload_to="admin_avatars/",
        blank=True,
        null=True,
        verbose_name="Profile Picture"
    )
    display_title = models.CharField(
        max_length=100,
        blank=True,
        default="Maison Administrator",
        verbose_name="Title / Role"
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Direct Telephone"
    )
    timezone = models.CharField(
        max_length=50,
        blank=True,
        default="Europe/Paris (CET)",
        verbose_name="Timezone"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Admin Profile"
        verbose_name_plural = "Admin Profiles"

    def __str__(self):
        return f"Profile of {self.user.username}"

    @classmethod
    def get_for_user(cls, user):
        """
        Safely fetch or create an AdminProfile for the given User.
        """
        profile, _ = cls.objects.get_or_create(user=user)
        return profile
