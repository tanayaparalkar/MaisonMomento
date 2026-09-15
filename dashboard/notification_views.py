from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from apps.notifications.models import Notification

@staff_member_required
def notification_center(request):
    """Admin Notification Center with filtering and pagination."""
    qs = Notification.objects.filter(target_type='admin')
    
    # Filtering
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unread':
        qs = qs.filter(is_read=False)
    elif filter_type == 'orders':
        qs = qs.filter(notification_type__in=['order_placed', 'order_status', 'order_issue'])
    elif filter_type == 'inventory':
        qs = qs.filter(notification_type__in=['low_stock', 'out_of_stock'])
    elif filter_type == 'products':
        qs = qs.filter(notification_type__in=['product_archived', 'product_restored'])

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "dashboard/notifications.html", {
        "page_obj": page_obj,
        "filter": filter_type,
    })

@staff_member_required
def mark_read(request, pk):
    """Mark a single notification as read."""
    if request.method == "POST":
        notif = get_object_or_404(Notification, pk=pk, target_type='admin')
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=['is_read', 'read_at'])
    return redirect('dashboard:notifications')

@staff_member_required
def mark_all_read(request):
    """Mark all unread admin notifications as read."""
    if request.method == "POST":
        Notification.objects.filter(target_type='admin', is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        messages.success(request, "All notifications marked as read.")
    return redirect('dashboard:notifications')
