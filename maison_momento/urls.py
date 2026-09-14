from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views

from apps.catalog import views as catalog_views

# Customize Django Admin branding
admin.site.site_header = "MAISON MOMENTO"
admin.site.site_title = "Maison Momento Luxury Perfumerie"
admin.site.index_title = "Retailer Administration Portal"

urlpatterns = [
    path("", RedirectView.as_view(url="/products/", permanent=True), name="home"),
    path("about/", catalog_views.about, name="about"),
    path("contact/", catalog_views.contact, name="contact"),
    path("collections/", catalog_views.collections, name="collections"),
    path("admin/analytics/", include("apps.analytics.urls")),
    # Standard Django Admin
    path("admin/", admin.site.urls),
    path("dashboard/", include("dashboard.urls")),
    path(
    "login/",
    auth_views.LoginView.as_view(
        template_name="registration/login.html"
    ),
    name="login",),
    path(
    "logout/",
    auth_views.LogoutView.as_view(
        next_page="login"
    ),
    name="logout",),
    path("products/", include("apps.catalog.urls")),
    path("cart/", include("apps.sales.urls")),
    path("account/", include("apps.customers.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
