"""
apps/catalog/views/search.py
============================
Apple Spotlight-inspired live AJAX search endpoint for the client storefront.

Searches ONLY:
  - Products (Fragrances)
  - Collections (Categories & Fragrance Families)
  - Static Pages (About, Contact, Catalogue, Discovery)

Strictly NOT:
  - Orders
  - Dashboard
  - Admin
  - Customer database
"""

import logging
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.urls import reverse

from ..models import Category, Product

logger = logging.getLogger(__name__)


def _serialize_product(product):
    """Serialize a Product instance into an elegant Spotlight search card payload."""
    primary_img = product.primary_image
    image_url = (
        primary_img.image.url
        if (primary_img and primary_img.image)
        else "https://images.unsplash.com/photo-1594035910387-fea47794261f?q=80&w=600&auto=format&fit=crop"
    )

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
        desc = (product.description or "").strip()
        words = desc.split()
        short_note = " ".join(words[:10]) + ("…" if len(words) > 10 else "")

    if product.category:
        collection_name = f"{product.category.name} Collection"
    elif product.fragrance_family:
        collection_name = f"{product.get_fragrance_family_display()} Collection"
    else:
        collection_name = "Fine Fragrance"

    effective_p = product.effective_price
    formatted_price = f"₹{int(effective_p):,}" if effective_p == int(effective_p) else f"₹{effective_p:,.2f}"

    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "category": collection_name,
        "price": formatted_price,
        "rating": product.average_rating,
        "image": image_url,
        "short_note": short_note,
        "detail_url": reverse("catalog:product_detail", kwargs={"pk": product.pk}),
        "in_stock": product.stock > 0,
        "stock_label": product.inventory_status_label,
    }


def spotlight_search_api(request):
    """
    Live AJAX search endpoint returning matching perfumes, collections, and pages
    formatted for the Apple Spotlight overlay.
    """
    raw_query = request.GET.get("q", "")
    query = raw_query.strip()

    # Define searchable storefront static pages
    static_pages = [
        {
            "title": "About Maison Moménto",
            "url": reverse("about"),
            "category": "Story & Heritage",
            "icon": "compass",
            "keywords": ["about", "story", "heritage", "craftsmanship", "maison", "founder", "atelier"],
        },
        {
            "title": "Concierge & Client Care",
            "url": reverse("contact"),
            "category": "Client Services",
            "icon": "message",
            "keywords": ["contact", "concierge", "support", "help", "phone", "email", "address", "boutique", "client care"],
        },
        {
            "title": "Fine Fragrance Catalogue",
            "url": reverse("catalog:product_list"),
            "category": "All Fragrances",
            "icon": "bottle",
            "keywords": ["fragrances", "catalog", "catalogue", "perfumes", "all", "shop", "explore"],
        },
        {
            "title": "Olfactory Collections",
            "url": reverse("collections"),
            "category": "Collections",
            "icon": "layers",
            "keywords": ["collections", "families", "accords", "woody", "floral", "citrus", "oud"],
        },
        {
            "title": "The Discovery Set",
            "url": reverse("discovery"),
            "category": "Curated Sets",
            "icon": "sparkle",
            "keywords": ["discovery", "sample", "set", "experience", "gift", "miniatures", "tester"],
        },
    ]

    # --- EMPTY STATE: Nothing is typed ---
    if not query:
        featured_qs = (
            Product.objects.filter(is_active=True, is_featured=True)
            .select_related("category")
            .prefetch_related("images", "top_notes", "heart_notes", "base_notes")[:4]
        )
        if not featured_qs.exists():
            featured_qs = (
                Product.objects.filter(is_active=True)
                .select_related("category")
                .prefetch_related("images", "top_notes", "heart_notes", "base_notes")[:4]
            )

        products_data = [_serialize_product(p) for p in featured_qs]

        categories_qs = Category.objects.filter(is_active=True).order_by("name")[:6]
        collections_data = [
            {
                "name": c.name,
                "category": f"{c.product_count} Fragrances",
                "detail_url": f"{reverse('catalog:product_list')}?category={c.slug}",
            }
            for c in categories_qs
        ]

        popular_searches = ["Royal Oud", "Bergamot", "Rose", "Discovery", "Woody", "Date Night"]

        return JsonResponse({
            "query": "",
            "is_empty_state": True,
            "popular_searches": popular_searches,
            "newest_fragrances": products_data,
            "collections": collections_data,
        })

    # --- LIVE QUERY: Search across Products, Collections, Pages ---
    q_lower = query.lower()

    # 1. Products search
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

    matching_ids = list(
        Product.objects.filter(is_active=True)
        .filter(filter_q)
        .values_list("id", flat=True)
        .distinct()
    )

    matched_products = (
        Product.objects.filter(id__in=matching_ids)
        .select_related("category")
        .prefetch_related("images", "top_notes", "heart_notes", "base_notes")
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
        .order_by("-relevance", "-is_featured", "name")[:6]
    )

    products_results = [_serialize_product(p) for p in matched_products]

    # 2. Collections search
    collections_matches = Category.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True
    ).order_by("name")[:4]

    collections_results = [
        {
            "name": c.name,
            "category": f"{c.product_count} Fragrances · Olfactory Collection",
            "detail_url": f"{reverse('catalog:product_list')}?category={c.slug}",
        }
        for c in collections_matches
    ]

    # 3. Static Pages search
    pages_results = []
    for page in static_pages:
        title_match = q_lower in page["title"].lower()
        keyword_match = any(q_lower in kw.lower() for kw in page["keywords"])
        if title_match or keyword_match:
            pages_results.append({
                "name": page["title"],
                "category": page["category"],
                "detail_url": page["url"],
                "icon": page["icon"],
            })

    total_count = len(products_results) + len(collections_results) + len(pages_results)

    return JsonResponse({
        "query": query,
        "is_empty_state": False,
        "count": total_count,
        "products": products_results,
        "collections": collections_results,
        "pages": pages_results,
    })
