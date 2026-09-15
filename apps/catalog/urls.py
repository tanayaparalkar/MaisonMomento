from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("<int:pk>/", views.product_detail, name="product_detail"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:pk>/", views.toggle_wishlist, name="toggle_wishlist"),
]