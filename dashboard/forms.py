from django import forms
from django.forms import inlineformset_factory
from apps.catalog.models import Product, ProductImage

class ProductForm(forms.ModelForm):
    """
    Form for creating and editing products.
    Stock is intentionally excluded and managed purely via Inventory Services.
    """
    class Meta:
        model = Product
        fields = [
            "name", "brand", "sku", "category", "gender", 
            "fragrance_family", "concentration", "occasions",
            "top_notes", "heart_notes", "base_notes",
            "price", "discount_price", "description", "is_featured", "is_active"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "fragrance_family": forms.Select(attrs={"class": "form-control"}),
            "concentration": forms.Select(attrs={"class": "form-control"}),
            "occasions": forms.CheckboxSelectMultiple(),
            "top_notes": forms.CheckboxSelectMultiple(),
            "heart_notes": forms.CheckboxSelectMultiple(),
            "base_notes": forms.CheckboxSelectMultiple(),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "discount_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("price")
        discount_price = cleaned_data.get("discount_price")

        if price and price <= 0:
            self.add_error("price", "Price must be greater than zero.")
            
        if price and discount_price:
            if discount_price >= price:
                self.add_error("discount_price", "Discount price must be less than the regular price.")
            if discount_price <= 0:
                self.add_error("discount_price", "Discount price must be greater than zero if provided.")

        return cleaned_data


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "is_primary", "display_order"]
        widgets = {
            "alt_text": forms.TextInput(attrs={"class": "form-control"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }

ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm, 
    extra=1, 
    can_delete=True
)


class VoucherForm(forms.ModelForm):
    """
    Administrative form for creating, editing, and scheduling promotional privilege vouchers.
    """
    class Meta:
        from apps.sales.models import Voucher
        model = Voucher
        fields = [
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_cart_value",
            "max_discount",
            "valid_from",
            "valid_until",
            "max_uses",
            "is_active",
            "specific_customer",
        ]
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. MAISON20, PRIVILEGE500",
                "style": "text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;",
            }),
            "description": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. 20% privilege on orders above ₹10,000",
            }),
            "discount_type": forms.Select(attrs={"class": "form-control"}),
            "discount_value": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "e.g. 15 for 15% or 500 for ₹500",
            }),
            "min_cart_value": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00",
            }),
            "max_discount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Optional cap in ₹",
            }),
            "valid_from": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "valid_until": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "max_uses": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "placeholder": "Leave empty for unlimited",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "specific_customer": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.valid_from:
                self.initial["valid_from"] = self.instance.valid_from.strftime("%Y-%m-%dT%H:%M")
            if self.instance.valid_until:
                self.initial["valid_until"] = self.instance.valid_until.strftime("%Y-%m-%dT%H:%M")
        elif "valid_from" not in self.initial:
            from django.utils import timezone
            self.initial["valid_from"] = timezone.now().strftime("%Y-%m-%dT%H:%M")

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if code:
            code = code.strip().upper()
        return code

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get("discount_type")
        discount_value = cleaned_data.get("discount_value")
        min_cart_value = cleaned_data.get("min_cart_value")
        valid_from = cleaned_data.get("valid_from")
        valid_until = cleaned_data.get("valid_until")

        if discount_value is not None:
            if discount_value <= 0:
                self.add_error("discount_value", "Discount value must be greater than zero.")
            elif discount_type == "percentage" and discount_value > 100:
                self.add_error("discount_value", "Percentage discount cannot exceed 100%.")

        if min_cart_value is not None and min_cart_value < 0:
            self.add_error("min_cart_value", "Minimum cart value cannot be negative.")

        if valid_from and valid_until and valid_until <= valid_from:
            self.add_error("valid_until", "Expiration date must be chronologically after the start date.")

        return cleaned_data


class BusinessSettingsForm(forms.ModelForm):
    """
    Form for editing centralized business contact and boutique information.
    """
    class Meta:
        from .models import BusinessSettings
        model = BusinessSettings
        fields = [
            "business_name",
            "business_email",
            "primary_phone",
            "secondary_phone",
            "whatsapp_number",
            "instagram_url",
            "business_address",
            "business_hours",
            "google_maps_url",
            "facebook_url",
            "linkedin_url",
            "twitter_url",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Maison Moménto",
            }),
            "business_email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "concierge@maisonmomento.com",
            }),
            "primary_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+33 1 40 20 50 50",
            }),
            "secondary_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+33 1 40 20 50 51 (optional)",
            }),
            "whatsapp_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+33 6 12 34 56 78 (optional)",
            }),
            "instagram_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://instagram.com/maisonmomento",
            }),
            "facebook_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://facebook.com/maisonmomento (optional)",
            }),
            "linkedin_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://linkedin.com/company/maisonmomento (optional)",
            }),
            "twitter_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://x.com/maisonmomento (optional)",
            }),
            "business_address": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "15 Rue de la Paix\n75002 Paris\nFrance",
            }),
            "business_hours": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Monday – Friday: 10:00 AM – 7:00 PM (CET)\nSaturday: 11:00 AM – 5:00 PM (CET)\nSunday: Closed",
            }),
            "google_maps_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://maps.google.com/?q=... (optional)",
            }),
        }

    def _normalize_url(self, field_name):
        val = self.cleaned_data.get(field_name)
        if val:
            val = val.strip()
            if val.startswith("http://") and not val.startswith("http://localhost") and not val.startswith("http://127.0.0.1"):
                val = "https://" + val[7:]
            elif not val.startswith(("http://", "https://")):
                val = f"https://{val}"
        return val

    def clean_instagram_url(self):
        return self._normalize_url("instagram_url")

    def clean_google_maps_url(self):
        return self._normalize_url("google_maps_url")

    def clean_facebook_url(self):
        return self._normalize_url("facebook_url")

    def clean_linkedin_url(self):
        return self._normalize_url("linkedin_url")

    def clean_twitter_url(self):
        return self._normalize_url("twitter_url")

    def clean_business_name(self):
        name = self.cleaned_data.get("business_name", "").strip()
        if not name:
            raise forms.ValidationError("Business Name is required.")
        return name

    def clean_business_email(self):
        email = self.cleaned_data.get("business_email", "").strip()
        if not email:
            raise forms.ValidationError("Business Email is required.")
        return email

    def clean_primary_phone(self):
        phone = self.cleaned_data.get("primary_phone", "").strip()
        if not phone:
            raise forms.ValidationError("Primary Phone Number is required.")
        return phone


