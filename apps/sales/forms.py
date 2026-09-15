from django import forms
from django.core.validators import RegexValidator

class CheckoutForm(forms.Form):
    first_name = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'sf-input', 'placeholder': 'Email Address'})
    )
    phone = forms.CharField(
        max_length=32,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Phone Number'})
    )
    address_line_1 = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Address Line 1'})
    )
    address_line_2 = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Address Line 2 (Optional)'})
    )
    city = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'City'})
    )
    state = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'State / Province'})
    )
    postal_code = forms.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\s\-]{4,10}$',
                message="Enter a valid postal code."
            )
        ],
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Postal Code'})
    )
    country = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Country'})
    )
    delivery_notes = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'sf-input', 'placeholder': 'Delivery Notes (Optional)', 'rows': 3})
    )

    def clean_email(self):
        return self.cleaned_data.get('email', '').strip()

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip()

    def clean_last_name(self):
        return self.cleaned_data.get('last_name', '').strip()
