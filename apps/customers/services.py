from .models import Customer

def get_customer_from_user(user):
    """
    Retrieves or creates a Customer instance for a given authenticated Django User.
    Returns None if the user is anonymous, None, or invalid.
    """
    if not user or not user.is_authenticated or not user.email:
        return None
        
    customer, created = Customer.objects.get_or_create(
        email=user.email,
        defaults={
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', '')
        }
    )
    
    return customer
