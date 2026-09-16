from django import forms
from django.core.validators import RegexValidator

COUNTRY_CHOICES = [
    ("India", "India"),
    ("United States", "United States"),
    ("United Kingdom", "United Kingdom"),
    ("United Arab Emirates", "United Arab Emirates"),
    ("France", "France"),
    ("Singapore", "Singapore"),
    ("Canada", "Canada"),
    ("Australia", "Australia"),
    ("Germany", "Germany"),
    ("Italy", "Italy"),
    ("Other", "Other Country"),
]

STATE_CHOICES = [
    ("Maharashtra", "Maharashtra"),
    ("Delhi", "Delhi / NCR"),
    ("Karnataka", "Karnataka"),
    ("Tamil Nadu", "Tamil Nadu"),
    ("Telangana", "Telangana"),
    ("Gujarat", "Gujarat"),
    ("West Bengal", "West Bengal"),
    ("Rajasthan", "Rajasthan"),
    ("Uttar Pradesh", "Uttar Pradesh"),
    ("Haryana", "Haryana"),
    ("Punjab", "Punjab"),
    ("Kerala", "Kerala"),
    ("Goa", "Goa"),
    ("Madhya Pradesh", "Madhya Pradesh"),
    ("Andhra Pradesh", "Andhra Pradesh"),
    ("Bihar", "Bihar"),
    ("Chandigarh", "Chandigarh"),
    ("Odisha", "Odisha"),
    ("Assam", "Assam"),
    ("Himachal Pradesh", "Himachal Pradesh"),
    ("Jammu & Kashmir", "Jammu & Kashmir"),
    ("Uttarakhand", "Uttarakhand"),
    ("Other", "Other State / Region"),
]

CITY_CHOICES = [
    ("Mumbai", "Mumbai"),
    ("New Delhi", "New Delhi"),
    ("Bengaluru", "Bengaluru"),
    ("Hyderabad", "Hyderabad"),
    ("Chennai", "Chennai"),
    ("Kolkata", "Kolkata"),
    ("Pune", "Pune"),
    ("Ahmedabad", "Ahmedabad"),
    ("Jaipur", "Jaipur"),
    ("Gurgaon", "Gurgaon"),
    ("Noida", "Noida"),
    ("Chandigarh", "Chandigarh"),
    ("Lucknow", "Lucknow"),
    ("Kochi", "Kochi"),
    ("Surat", "Surat"),
    ("Indore", "Indore"),
    ("Panaji", "Panaji / Goa"),
    ("Nagpur", "Nagpur"),
    ("Coimbatore", "Coimbatore"),
    ("Vadodara", "Vadodara"),
    ("Visakhapatnam", "Visakhapatnam"),
    ("Bhopal", "Bhopal"),
    ("Other", "Other City"),
]


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
        widget=forms.EmailInput(attrs={'class': 'sf-input', 'placeholder': 'name@example.com'})
    )
    phone = forms.CharField(
        max_length=32,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': '+91 98765 43210'})
    )
    address_line_1 = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Street Address, Apartment, Suite'})
    )
    address_line_2 = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'Landmark, Building Name (Optional)'})
    )
    country = forms.CharField(
        max_length=100,
        initial="India",
        widget=forms.Select(choices=COUNTRY_CHOICES, attrs={'class': 'sf-input sf-select', 'id': 'id_country'})
    )
    state = forms.CharField(
        max_length=100,
        initial="Maharashtra",
        widget=forms.Select(choices=STATE_CHOICES, attrs={'class': 'sf-input sf-select', 'id': 'id_state'})
    )
    city = forms.CharField(
        max_length=100,
        initial="Mumbai",
        widget=forms.Select(choices=CITY_CHOICES, attrs={'class': 'sf-input sf-select', 'id': 'id_city'})
    )
    postal_code = forms.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\s\-]{4,10}$',
                message="Enter a valid postal code."
            )
        ],
        widget=forms.TextInput(attrs={'class': 'sf-input', 'placeholder': 'PIN / Postal Code'})
    )
    delivery_notes = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'sf-input sf-textarea', 'placeholder': 'Special delivery instructions, gate code, or gift note (Optional)', 'rows': 3})
    )

    def clean_email(self):
        return self.cleaned_data.get('email', '').strip()

    def clean_first_name(self):
        return self.cleaned_data.get('first_name', '').strip()

    def clean_last_name(self):
        return self.cleaned_data.get('last_name', '').strip()
