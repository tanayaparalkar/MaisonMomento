from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("", views.cart_view, name="cart"),
    path("api/action/", views.cart_action, name="cart_action"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("payment/verify/", views.payment_verify, name="payment_verify"),
    path("payment/retry/<str:order_number>/", views.payment_retry, name="payment_retry"),
    path("order/<str:order_number>/", views.order_confirmation, name="order_confirmation"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
]
