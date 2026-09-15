"""
apps/catalog/views/collections.py
====================================
Collections view — one page per category with prefetch optimisation.
"""

from django.db.models import Count, Q, prefetch_related_objects
from django.shortcuts import render

from ..models import Category


def collections(request):
    categories = list(
        Category.objects
        .annotate(
            num_products=Count('products', filter=Q(products__is_active=True))
        )
        .filter(num_products__gt=0, is_active=True)
        .order_by('-num_products', 'name')
        .prefetch_related('products')
    )

    # Extract only the products that will actually be rendered (top 6 per category)
    # — slicing happens in Python memory after the prefetch
    rendered_products = []
    for category in categories:
        rendered_products.extend(list(category.products.all())[:6])

    # Only fetch images for products we are actually displaying
    prefetch_related_objects(rendered_products, 'images')

    return render(request, "catalog/collections.html", {
        "categories": categories,
    })
