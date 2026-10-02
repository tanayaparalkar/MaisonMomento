from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    # Customer Account & Profile
    path("", views.account_profile, name="profile"),
    path("login/", views.customer_login, name="login"),
    path("register/", views.customer_register, name="register"),
    path("logout/", views.customer_logout, name="logout"),
    path("update-profile/", views.update_profile, name="update_profile"),
    path("update-address/", views.update_address, name="update_address"),
    path("upload-avatar/", views.upload_avatar, name="upload_avatar"),
    path("change-password/", views.change_password, name="change_password"),

    # Notifications
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
]
