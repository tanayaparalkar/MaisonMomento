from django.urls import path
from . import views
from . import product_views
from . import order_views
from . import export_views
from . import inventory_views
from . import notification_views

app_name = "dashboard"

urlpatterns = [
    # Dashboard Home
    path("", views.dashboard, name="dashboard"),
    
    # Notifications (Phase 11)
    path("notifications/", notification_views.notification_center, name="notifications"),
    path("notifications/<int:pk>/read/", notification_views.mark_read, name="notification_mark_read"),
    path("notifications/read-all/", notification_views.mark_all_read, name="notification_mark_all_read"),
    
    # Products (Phase 10A)
    path("products/", product_views.products, name="products"),
    path("products/create/", product_views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", product_views.product_edit, name="product_edit"),
    
    # Orders (Phase 10B)
    path("orders/", order_views.orders, name="orders"),
    path("orders/<int:pk>/", order_views.order_detail, name="order_detail"),
    path("orders/<int:pk>/transition/", order_views.order_transition, name="order_transition"),
    
    # Inventory (Phase 9B/10A)
    path("inventory/", views.inventory, name="inventory"),
    path("inventory/adjust/<int:product_id>/", inventory_views.adjust_stock_action, name="adjust_stock"),
    path("inventory/history/<int:product_id>/", inventory_views.stock_history, name="stock_history"),
    
    # Exports (Phase 10B)
    path("export/", export_views.export_data, name="export_data"),
    
    # Others
    path("recommendations/", views.recommendations, name="recommendations"),
    path("clients/", views.clients, name="clients"),
    path("settings/", views.settings, name="settings"),
]
