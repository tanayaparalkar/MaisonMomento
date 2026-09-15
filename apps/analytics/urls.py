from django.urls import path
from .views import admin_analytics_dashboard

urlpatterns = [
    path("", admin_analytics_dashboard, name="admin_analytics_dashboard"),
]
