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
            "fragrance_family", "concentration", "price", 
            "discount_price", "description", "is_featured", "is_active"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "fragrance_family": forms.Select(attrs={"class": "form-control"}),
            "concentration": forms.Select(attrs={"class": "form-control"}),
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
