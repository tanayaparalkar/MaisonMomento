from .models import Customer

def get_customer_from_user(user):
    """
    Retrieves or creates a Customer instance for a given authenticated Django User.
    Returns None if the user is anonymous, None, or invalid.
    """
    if not user or not user.is_authenticated:
        return None
        
    customer = Customer.objects.filter(user=user).first()
    if customer:
        return customer

    email = user.email.strip() if getattr(user, 'email', None) else f"{user.username}@maisonmomento.com"
        
    customer = Customer.objects.filter(email__iexact=email).first()
    if customer:
        if not customer.user:
            customer.user = user
            customer.save(update_fields=['user'])
        return customer

    customer = Customer.objects.create(
        user=user,
        email=email,
        first_name=getattr(user, 'first_name', '') or user.username,
        last_name=getattr(user, 'last_name', '')
    )
    return customer

