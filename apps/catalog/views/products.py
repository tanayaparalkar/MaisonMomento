"""
apps/catalog/views/products.py
================================
Product listing and detail views.

Private helpers (prefixed with _) keep product_list() readable.
They are not imported by urls.py and not part of the public API.
"""

import logging
import re

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.recommendations.engine import RecommendationEngine
from apps.recommendations.services import (
    RecommendationLogger,
    RecommendationService,
)

from ..models import Category, Product

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers for product_list()
# ---------------------------------------------------------------------------

def _build_search_queryset(queryset, query):
    """Apply full-text-style search across name, brand, and category."""
    if not query:
        return queryset
    clean_query = re.sub(r'\s+', ' ', query.strip())
    if clean_query:
        queryset = queryset.filter(
            Q(name__icontains=clean_query) |
            Q(brand__icontains=clean_query) |
            Q(category__name__icontains=clean_query)
        )
    return queryset


def _apply_filters(queryset, category_slug, family, gender):
    """Apply sidebar filter parameters to the queryset."""
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    if family:
        queryset = queryset.filter(fragrance_family=family)
    if gender:
        queryset = queryset.filter(gender=gender)
    return queryset


def _apply_sort(queryset, sort):
    """Apply sort order to the queryset."""
    if sort == 'newest':
        return queryset.order_by('-updated_at', 'id')
    elif sort == 'alpha':
        return queryset.order_by('name', 'id')
    elif sort == 'price_asc':
        return queryset.order_by('price', 'id')
    elif sort == 'price_desc':
        return queryset.order_by('-price', 'id')
    else:  # featured / default
        return queryset.order_by('-is_featured', '-updated_at', 'id')


def _paginate_products(queryset, page_number, per_page=12):
    """Paginate the queryset and return a page object."""
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(page_number)


def _build_filter_context(request, query, category_slug, family, gender, categories):
    """
    Build the active-filter chip list and the pagination query string.

    Returns (active_filters, query_string).
    """
    get_copy = request.GET.copy()
    active_filters = []

    if query and query.strip():
        q_copy = get_copy.copy()
        q_copy.pop('q', None)
        q_copy.pop('page', None)
        active_filters.append({
            'name': f"Search: {query.strip()}",
            'remove_url': '?' + q_copy.urlencode() if q_copy else '?'
        })

    if category_slug:
        cat_copy = get_copy.copy()
        cat_copy.pop('category', None)
        cat_copy.pop('page', None)
        cat_obj = categories.filter(slug=category_slug).first()
        active_filters.append({
            'name': cat_obj.name if cat_obj else category_slug.title(),
            'remove_url': '?' + cat_copy.urlencode() if cat_copy else '?'
        })

    if family:
        fam_copy = get_copy.copy()
        fam_copy.pop('family', None)
        fam_copy.pop('page', None)
        fam_dict = dict(Product.FRAGRANCE_FAMILY_CHOICES)
        active_filters.append({
            'name': fam_dict.get(family, family.title()),
            'remove_url': '?' + fam_copy.urlencode() if fam_copy else '?'
        })

    if gender:
        gen_copy = get_copy.copy()
        gen_copy.pop('gender', None)
        gen_copy.pop('page', None)
        gen_dict = dict(Product.GENDER_CHOICES)
        active_filters.append({
            'name': gen_dict.get(gender, gender.title()),
            'remove_url': '?' + gen_copy.urlencode() if gen_copy else '?'
        })

    # Pagination query string preserves all active filters/sort but removes 'page'
    qs_copy = get_copy.copy()
    qs_copy.pop('page', None)
    query_string = qs_copy.urlencode()

    return active_filters, query_string


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def product_list(request):
    queryset = (
        Product.objects
        .filter(is_active=True)
        .select_related("category")
        .prefetch_related("images")
    )

    # Read GET params
    query        = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    family       = request.GET.get('family', '')
    gender       = request.GET.get('gender', '')
    sort         = request.GET.get('sort', 'featured')
    page_number  = request.GET.get('page')

    # Build queryset through helpers
    queryset = _build_search_queryset(queryset, query)
    queryset = _apply_filters(queryset, category_slug, family, gender)
    queryset = _apply_sort(queryset, sort)
    page_obj  = _paginate_products(queryset, page_number)

    categories = Category.objects.filter(is_active=True).order_by('name')
    active_filters, query_string = _build_filter_context(
        request, query, category_slug, family, gender, categories
    )

    # Check for Scent Finder Questionnaire submission
    is_quiz = request.GET.get('scent_quiz') == '1' or bool(request.GET.get('scent_pref'))
    quiz_results = None
    quiz_answers = {}
    purpose = request.GET.get('purpose', 'myself')

    if is_quiz:
        notes_raw = request.GET.getlist('notes')
        if not notes_raw and request.GET.get('notes_csv'):
            notes_raw = [n.strip() for n in request.GET.get('notes_csv').split(',') if n.strip()]

        quiz_answers = {
            'purpose': purpose,
            'scent_pref': request.GET.get('scent_pref', ''),
            'notes': notes_raw,
            'vibe': request.GET.get('vibe', ''),
            'wear_time': request.GET.get('wear_time', ''),
            'strength': request.GET.get('strength', ''),
            'budget': request.GET.get('budget', ''),
            'target_audience': request.GET.get('target_audience', ''),
        }
        quiz_results = RecommendationEngine.recommend_from_quiz(quiz_answers, purpose=purpose, limit=12)

        pref_name = quiz_answers.get('scent_pref')
        if purpose == "gifting":
            chip_title = f"Gift Curations: {pref_name}" if pref_name else "Gift Curations"
        else:
            chip_title = f"Suggested: {pref_name}" if pref_name else "Curated Suggestions"
        active_filters.append({
            'name': chip_title,
            'remove_url': '?'
        })

    # Recommendations are suppressed while filters or quiz are active
    is_filtering = bool(
        query or category_slug or family or gender
        or is_quiz
        or (page_number and page_number != '1')
        or (sort != 'featured')
    )

    rec_payload = {"trending": [], "recent": [], "recommended": []}
    if not is_filtering and not is_quiz:
        visitor = getattr(request, 'visitor', None)
        rec_payload = RecommendationService.get_homepage_context(visitor)

    context = {
        "page_obj":       page_obj,
        "categories":     categories,
        "families":       Product.FRAGRANCE_FAMILY_CHOICES,
        "genders":        Product.GENDER_CHOICES,
        "active_filters": active_filters,
        "query_string":   query_string,
        "current_sort":   sort,
        "current_query":  query,
        "is_filtering":   is_filtering,
        "is_quiz":        is_quiz,
        "quiz_results":   quiz_results,
        "quiz_answers":   quiz_answers,
        "quiz_purpose":   purpose,
        **rec_payload,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.GET.get('format') == 'json':
        items_data = []
        if quiz_results:
            for item in quiz_results:
                prod = item['product']
                img_url = prod.primary_image.image.url if prod.primary_image and prod.primary_image.image else None
                items_data.append({
                    'id': prod.id,
                    'name': prod.name,
                    'brand': prod.brand,
                    'price': f"{prod.effective_price:.2f}",
                    'image': img_url,
                    'detail_url': f"/products/{prod.id}/",
                    'match_percentage': item['match_percentage'],
                    'match_reason': item['match_reason'],
                    'is_gifting': item['is_gifting'],
                })
        return JsonResponse({'is_quiz': True, 'results': items_data})

    return render(request, "catalog/product_list.html", context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)

    # Log the view interaction — never let logging failures break the page
    if hasattr(request, "visitor") and request.visitor:
        try:
            RecommendationLogger.log(
                visitor=request.visitor,
                product=product,
                event_type="view",
            )
        except Exception:
            logger.exception("RecommendationLogger failed for product pk=%s", pk)

    # Similar products via the service layer — engine details stay hidden from the view
    similar_products = RecommendationService.get_similar_products(product)

    breadcrumbs = [
        {"name": "Home",        "url": "/"},
        {"name": "Fragrances",  "url": "/products/"},
        {"name": product.name,  "url": ""},
    ]

    return render(
        request,
        "catalog/product_detail.html",
        {
            "product":          product,
            "similar_products": similar_products,
            "breadcrumbs":      breadcrumbs,
        }
    )
