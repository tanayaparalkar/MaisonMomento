from apps.customers.models import Customer
from apps.customers.services import get_customer_from_user
from apps.sales.models import Cart

def cart_data(request):
    """
    Exposes cart_item_count for authenticated customers.
    """
    if not request.user.is_authenticated:
        return {'cart_item_count': 0}
        
    customer = get_customer_from_user(request.user)
    if not customer:
        return {'cart_item_count': 0}
        
    try:
        cart = Cart.objects.get(customer=customer)
        return {'cart_item_count': cart.total_items}
    except Cart.DoesNotExist:
        return {'cart_item_count': 0}
