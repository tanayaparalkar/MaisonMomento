import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maison_momento.settings')
django.setup()

from apps.notifications.models import Notification
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

notif = Notification.objects.filter(target_type='admin').order_by('-created_at').first()

c = Client(SERVER_NAME='127.0.0.1')
c.force_login(user)

c.post(f'/dashboard/notifications/{notif.pk}/read/')
notif.refresh_from_db()
print("Notif is_read after mark-read:", notif.is_read)

# Unread count again
resp_dash2 = c.get('/dashboard/')
print("Unread count in dash context after mark read?", "notification-indicator" in resp_dash2.content.decode('utf-8'))

