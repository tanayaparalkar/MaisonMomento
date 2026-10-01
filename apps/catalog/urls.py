from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("discovery/", views.discovery_collection_view, name="discovery_collection"),
    path("<int:pk>/", views.product_detail, name="product_detail"),
    path("<int:pk>/reviews/add/", views.submit_review, name="submit_review"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:pk>/", views.toggle_wishlist, name="toggle_wishlist"),
]