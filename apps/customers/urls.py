from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
]
