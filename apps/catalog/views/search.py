"""
apps/catalog/views/search.py
============================
Apple Spotlight-inspired live AJAX search endpoint for the client storefront.

Searches across:
  - Product Name
  - Brand
  - Collection / Category
  - Fragrance Family
  - Top Notes
  - Heart Notes
  - Base Notes
  - Occasions
  - Short Description
"""

import logging
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.urls import reverse

from ..models import Product

logger = logging.getLogger(__name__)


def _serialize_product(product, query=""):
    """Serialize a Product instance into an elegant Spotlight search card payload."""
    primary_img = product.primary_image
    image_url = (
        primary_img.image.url
        if (primary_img and primary_img.image)
        else "https://images.unsplash.com/photo-1594035910387-fea47794261f?q=80&w=600&auto=format&fit=crop"
    )

    # Build concise olfactory notes string (e.g. "Bergamot · Rose · Oud")
    notes_list = []
    for n in product.top_notes.all()[:2]:
        notes_list.append(n.name)
    for n in product.heart_notes.all()[:2]:
        if n.name not in notes_list:
            notes_list.append(n.name)
    for n in product.base_notes.all()[:2]:
        if n.name not in notes_list:
            notes_list.append(n.name)

    if notes_list:
        short_note = " · ".join(notes_list[:4])
    else:
        # Fallback to truncated description
        desc = (product.description or "").strip()
        words = desc.split()
        short_note = " ".join(words[:12]) + ("…" if len(words) > 12 else "")

    # Collection display name
    if product.category:
        collection_name = f"{product.category.name} Collection"
    elif product.fragrance_family:
        collection_name = f"{product.get_fragrance_family_display()} Collection"
    else:
        collection_name = "Fine Fragrance"

    # Price formatting
    effective_p = product.effective_price
    formatted_price = f"₹{int(effective_p):,}" if effective_p == int(effective_p) else f"₹{effective_p:,.2f}"

    original_p = None
    if product.discount_price and product.discount_price < product.price:
        orig = product.price
        original_p = f"₹{int(orig):,}" if orig == int(orig) else f"₹{orig:,.2f}"

    # Occasions
    occasions = [o.name for o in product.occasions.all()[:3]]

    # Detail URL
    detail_url = reverse("catalog:product_detail", kwargs={"pk": product.pk})

    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "collection": collection_name,
        "price": formatted_price,
        "original_price": original_p,
        "rating": product.average_rating,
        "review_count": product.review_count,
        "image": image_url,
        "short_note": short_note,
        "occasions": occasions,
        "detail_url": detail_url,
        "in_stock": product.stock > 0,
        "stock_label": product.inventory_status_label,
    }


def spotlight_search_api(request):
    """
    Live AJAX search endpoint returning matching perfumes formatted for
    the Apple Spotlight overlay.
    """
    raw_query = request.GET.get("q", "")
    query = raw_query.strip()

    # If query is empty, return curated featured fragrances as the initial spotlight view
    if not query:
        featured_qs = (
            Product.objects.filter(is_active=True, is_featured=True)
            .select_related("category")
            .prefetch_related("images", "top_notes", "heart_notes", "base_notes", "occasions")[:4]
        )
        if not featured_qs.exists():
            featured_qs = (
                Product.objects.filter(is_active=True)
                .select_related("category")
                .prefetch_related("images", "top_notes", "heart_notes", "base_notes", "occasions")[:4]
            )

        results = [_serialize_product(p) for p in featured_qs]
        return JsonResponse({
            "query": "",
            "count": len(results),
            "results": results,
            "is_featured_curation": True,
        })

    # Search filter across all dimensions
    filter_q = (
        Q(name__icontains=query)
        | Q(brand__icontains=query)
        | Q(description__icontains=query)
        | Q(category__name__icontains=query)
        | Q(fragrance_family__icontains=query)
        | Q(top_notes__name__icontains=query)
        | Q(heart_notes__name__icontains=query)
        | Q(base_notes__name__icontains=query)
        | Q(occasions__name__icontains=query)
    )

    # Distinct IDs matching the query to avoid SQL join row multiplication
    matching_ids = list(
        Product.objects.filter(is_active=True)
        .filter(filter_q)
        .values_list("id", flat=True)
        .distinct()
    )

    if not matching_ids:
        return JsonResponse({
            "query": query,
            "count": 0,
            "results": [],
            "is_featured_curation": False,
        })

    # Fetch matching products cleanly and rank
    products = (
        Product.objects.filter(id__in=matching_ids)
        .select_related("category")
        .prefetch_related("images", "top_notes", "heart_notes", "base_notes", "occasions")
        .annotate(
            relevance=Case(
                When(name__istartswith=query, then=Value(10)),
                When(name__icontains=query, then=Value(8)),
                When(category__name__iexact=query, then=Value(6)),
                When(fragrance_family__iexact=query, then=Value(5)),
                When(description__icontains=query, then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("-relevance", "-is_featured", "name")
    )

    # Deduplicate in python preservation of order
    seen_ids = set()
    unique_products = []
    for p in products:
        if p.id not in seen_ids:
            seen_ids.add(p.id)
            unique_products.append(p)
            if len(unique_products) >= 12:
                break

    results = [_serialize_product(p, query=query) for p in unique_products]

    return JsonResponse({
        "query": query,
        "count": len(results),
        "results": results,
        "is_featured_curation": False,
    })
