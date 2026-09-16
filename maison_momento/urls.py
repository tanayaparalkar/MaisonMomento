from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views

from apps.catalog import views as catalog_views

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=settings.STATIC_URL + "favicon.ico", permanent=True)),
    path("", RedirectView.as_view(url="/products/", permanent=True), name="home"),
    path("about/", catalog_views.about, name="about"),
    path("contact/", catalog_views.contact, name="contact"),
    path("collections/", catalog_views.collections, name="collections"),
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

# Serve media files in both development and production (Render)
from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
