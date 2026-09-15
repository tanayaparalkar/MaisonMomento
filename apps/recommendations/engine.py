from django.db.models import Count, Q, Case, When, prefetch_related_objects

from apps.catalog.models import Product
from apps.recommendations.models import Interaction


class RecommendationEngine:
    """
    Core recommendation engine.

    All recommendation logic should live here.
    """

    @staticmethod
    def trending_products(limit=6):
        interactions = (
            Interaction.objects
            .values("product")
            .annotate(score=Count("id"))
            .order_by("-score")
        )

        product_ids = [i["product"] for i in interactions[:limit]]
        
        if not product_ids:
            return Product.objects.none()
            
        preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(product_ids)])

        return Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).prefetch_related('images').order_by(preserved)

    @staticmethod
    def recently_viewed(visitor, limit=6):
        """
        Returns the visitor's most recently viewed products.
        """

        if visitor is None:
            return Product.objects.none()

        interactions = (
            Interaction.objects
            .filter(
                visitor=visitor,
                event_type="view"
            )
            .select_related("product")
            .order_by("-created_at")
        )

        seen = set()
        products = []

        for interaction in interactions:
            if interaction.product.id not in seen:
                seen.add(interaction.product.id)
                products.append(interaction.product)

            if len(products) >= limit:
                break
                
        prefetch_related_objects(products, 'images')

        return products
    
    @staticmethod
    def similar_products(product, limit=6):
        """
        Recommend products from the same category.
        """

        if product is None:
            return Product.objects.none()

        return (
            Product.objects.filter(
                category=product.category,
                is_active=True
            ).prefetch_related('images')
            .exclude(id=product.id)[:limit]
        )

    @staticmethod
    def recommend_for_visitor(visitor, limit=6):
        if visitor is None:
            return RecommendationEngine.trending_products(limit)
            
        visitor_categories = Interaction.objects.filter(visitor=visitor).values_list("product__category", flat=True).distinct()
        viewed_products = Interaction.objects.filter(visitor=visitor).values_list("product", flat=True)
        
        interactions = (
            Interaction.objects
            .filter(product__category__in=visitor_categories)
            .exclude(product__in=viewed_products)
            .values("product")
            .annotate(score=Count("id"))
            .order_by("-score")
        )

        product_ids = [i["product"] for i in interactions[:limit]]
        
        if not product_ids:
            return RecommendationEngine.trending_products(limit)
            
        preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(product_ids)])

        return Product.objects.filter(
            id__in=product_ids,
            is_active=True
        ).prefetch_related('images').order_by(preserved)