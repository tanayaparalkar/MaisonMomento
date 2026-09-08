from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from apps.catalog.models import Product
from .models import UserInteraction


def get_recommendations(user=None, session_id=None, limit=5):
    """
    Modular category-based recommendation service.
    
    Workflow:
    1. Retrieve interactions for the given user or session_id.
    2. Group interactions by category and apply simple recency weighting:
       - Last 7 days: weight 2.0
       - 8 to 30 days: weight 1.0
       - Older than 30 days: weight 0.5
    3. Rank categories in descending order of weighted interaction count.
    4. Select active, in-stock products from those ranked categories,
       prioritizing the highest-weighted category first.
    5. Fallback to featured / in-stock products if user has no/few interactions.
    """
    if limit <= 0:
        return []

    interaction_filter = Q()
    if user is not None:
        interaction_filter |= Q(user=user)
    if session_id:
        interaction_filter |= Q(session_id=session_id)

    ranked_categories = []
    interacted_product_ids = set()

    if interaction_filter:
        interactions = UserInteraction.objects.filter(interaction_filter).select_related("category", "product")
        
        if interactions.exists():
            now = timezone.now()
            category_scores = {}

            for interaction in interactions:
                interacted_product_ids.add(interaction.product_id)
                cat_id = interaction.category_id
                if not cat_id:
                    continue

                age = now - interaction.created_at
                # Recency weighting
                if age <= timedelta(days=7):
                    weight = 2.0
                elif age <= timedelta(days=30):
                    weight = 1.0
                else:
                    weight = 0.5

                # Additional small weight for clicks vs views
                action_weight = 1.2 if interaction.interaction_type == "PRODUCT_CLICK" else 1.0

                category_scores[cat_id] = category_scores.get(cat_id, 0.0) + (weight * action_weight)

            # Rank categories by score descending
            ranked_categories = sorted(
                category_scores.keys(),
                key=lambda cid: category_scores[cid],
                reverse=True
            )

    recommended_products = []
    seen_product_ids = set()

    # Step 4: Pick products from ranked categories in order of preference
    for cat_id in ranked_categories:
        products_in_cat = (
            Product.objects.filter(category_id=cat_id, is_active=True, stock__gt=0)
            .exclude(id__in=seen_product_ids)
            .order_by("-is_featured", "-created_at")
        )
        for product in products_in_cat:
            recommended_products.append(product)
            seen_product_ids.add(product.id)
            if len(recommended_products) >= limit:
                break
        if len(recommended_products) >= limit:
            break

    # Step 5: Fallback if we still need more recommendations to satisfy limit
    if len(recommended_products) < limit:
        remaining_needed = limit - len(recommended_products)
        fallback_products = (
            Product.objects.filter(is_active=True, stock__gt=0)
            .exclude(id__in=seen_product_ids)
            .order_by("-is_featured", "-created_at")[:remaining_needed]
        )
        for product in fallback_products:
            recommended_products.append(product)
            seen_product_ids.add(product.id)

    return recommended_products[:limit]
