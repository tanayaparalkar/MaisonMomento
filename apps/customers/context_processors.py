from apps.customers.models import Customer, Wishlist
from apps.customers.services import get_customer_from_user

def wishlist_data(request):
    """
    Exposes wishlist_count and wishlisted_product_ids for authenticated customers.
    Performs a single optimized query.
    """
    if not request.user.is_authenticated:
        return {
            'wishlist_count': 0,
            'wishlisted_product_ids': set()
        }
        
    customer = get_customer_from_user(request.user)
    if not customer:
        return {
            'wishlist_count': 0,
            'wishlisted_product_ids': set()
        }
        
    # Fetch only the product IDs to avoid heavy queries
    wishlisted_ids = set(Wishlist.objects.filter(customer=customer).values_list('product_id', flat=True))
    
    return {
        'wishlist_count': len(wishlisted_ids),
        'wishlisted_product_ids': wishlisted_ids
    }

def customer_notifications_data(request):
    """
    Exposes unread_customer_notifications_count for authenticated users.
    """
    if request.user.is_authenticated:
        from apps.notifications.models import Notification
        count = Notification.objects.filter(target_type='customer', recipient=request.user, is_read=False).count()
        return {'unread_customer_notifications_count': count}
    return {'unread_customer_notifications_count': 0}
