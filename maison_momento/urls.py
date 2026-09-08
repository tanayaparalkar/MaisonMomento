from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

# Customize Django Admin branding
admin.site.site_header = "MAISON MOMENTO"
admin.site.site_title = "Maison Momento Luxury Perfumerie"
admin.site.index_title = "Retailer Administration Portal"

urlpatterns = [
    # Custom Analytics Dashboard Route inside admin namespace
    path("admin/analytics/", include("apps.analytics.urls")),
    
    # Standard Django Admin
    path("admin/", admin.site.urls),
    
    # Root redirect to Admin
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
