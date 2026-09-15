"""
apps/catalog/views/wishlist.py
================================
Wishlist view and AJAX toggle endpoint.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.customers.models import Wishlist
from apps.customers.services import get_customer_from_user

from ..models import Product

logger = logging.getLogger(__name__)


@login_required
def wishlist_view(request):
    customer = get_customer_from_user(request.user)
    if not customer:
        return render(request, "catalog/wishlist.html", {"products": []})

    wishlist_items = (
        Wishlist.objects
        .filter(customer=customer)
        .select_related('product', 'product__category')
        .prefetch_related('product__images')
    )
    products = [item.product for item in wishlist_items]

    return render(request, "catalog/wishlist.html", {"products": products})


@require_POST
def toggle_wishlist(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({
            "authenticated": False,
            "login_url": f"{reverse('login')}?next={request.META.get('HTTP_REFERER', '/')}"
        })

    customer = get_customer_from_user(request.user)
    if not customer:
        return JsonResponse({"error": "Invalid user"}, status=400)

    product = get_object_or_404(Product, pk=pk)
    wishlist_item = Wishlist.objects.filter(customer=customer, product=product).first()

    if wishlist_item:
        wishlist_item.delete()
        is_wishlisted = False
    else:
        Wishlist.objects.create(customer=customer, product=product)
        is_wishlisted = True

    count = Wishlist.objects.filter(customer=customer).count()
    logger.debug(
        "Wishlist toggle: customer=%s product=%s wishlisted=%s",
        customer.pk, pk, is_wishlisted,
    )
    return JsonResponse({
        "authenticated": True,
        "is_wishlisted": is_wishlisted,
        "count": count,
    })
