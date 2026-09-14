from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from apps.notifications.models import Notification

@login_required
def notifications(request):
    """Customer notifications page."""
    qs = Notification.objects.filter(target_type='customer', recipient=request.user)
    
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'customers/notifications.html', {
        'page_obj': page_obj
    })

@login_required
def mark_notification_read(request, pk):
    """Mark a customer notification as read."""
    if request.method == "POST":
        notif = get_object_or_404(Notification, pk=pk, target_type='customer', recipient=request.user)
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=['is_read', 'read_at'])
    return redirect('customers:notifications')
