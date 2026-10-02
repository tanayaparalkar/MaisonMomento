from apps.notifications.models import Notification

def unread_admin_notifications(request):
    if request.user.is_authenticated and request.user.is_staff:
        count = Notification.objects.filter(target_type='admin', is_read=False).count()
        return {'unread_admin_notifications_count': count}
    return {'unread_admin_notifications_count': 0}


def business_contact_info(request):
    """
    Exposes centralized business contact settings to all templates.
    """
    try:
        from dashboard.models import BusinessSettings
        return {
            "contact_info": BusinessSettings.get_settings()
        }
    except Exception:
        return {"contact_info": None}


def admin_profile_context(request):
    """
    Exposes AdminProfile instance for authenticated staff members.
    """
    if getattr(request, "user", None) and request.user.is_authenticated and request.user.is_staff:
        try:
            from dashboard.models import AdminProfile
            return {
                "admin_profile": AdminProfile.get_for_user(request.user)
            }
        except Exception:
            return {"admin_profile": None}
    return {"admin_profile": None}

