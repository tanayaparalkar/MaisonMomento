from django.urls import path
from . import views
from . import product_views
from . import order_views
from . import export_views
from . import inventory_views
from . import notification_views
from . import review_views
from . import voucher_views

app_name = "dashboard"

urlpatterns = [
    # Dashboard Home
    path("", views.dashboard, name="dashboard"),
    
    # Insights (Analytics & Charts)
    path("insights/", views.insights, name="insights"),
    
    # Notifications (Phase 11)
    path("notifications/", notification_views.notification_center, name="notifications"),
    path("notifications/<int:pk>/read/", notification_views.mark_read, name="notification_mark_read"),
    path("notifications/read-all/", notification_views.mark_all_read, name="notification_mark_all_read"),
    
    # Catalogue Management
    path("products/", product_views.products, name="products"),
    path("products/new/", product_views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", product_views.product_edit, name="product_edit"),
    path("categories/", product_views.categories, name="categories"),
    
    # Reviews Management
    path("reviews/", review_views.reviews, name="reviews"),
    path("reviews/<int:pk>/toggle/", review_views.review_toggle_approval, name="review_toggle"),
    path("reviews/<int:pk>/edit/", review_views.review_edit, name="review_edit"),
    path("reviews/<int:pk>/delete/", review_views.review_delete, name="review_delete"),
    
    # Privilege Vouchers
    path("vouchers/", voucher_views.vouchers, name="vouchers"),
    path("vouchers/new/", voucher_views.voucher_create, name="voucher_create"),
    path("vouchers/<int:pk>/edit/", voucher_views.voucher_edit, name="voucher_edit"),
    path("vouchers/<int:pk>/toggle/", voucher_views.voucher_toggle, name="voucher_toggle"),
    path("vouchers/<int:pk>/delete/", voucher_views.voucher_delete, name="voucher_delete"),
    
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
