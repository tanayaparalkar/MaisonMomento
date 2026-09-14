from apps.notifications.models import Notification

def unread_admin_notifications(request):
    if request.user.is_authenticated and request.user.is_staff:
        count = Notification.objects.filter(target_type='admin', is_read=False).count()
        return {'unread_admin_notifications_count': count}
    return {'unread_admin_notifications_count': 0}
