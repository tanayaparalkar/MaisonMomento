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

    @staticmethod
    def recommend_from_quiz(answers, purpose="myself", limit=12):
        """
        Intelligently score and rank products based on scent questionnaire responses.
        Handles both personal recommendations and curated gifting.
        """
        products = (
            Product.objects
            .filter(is_active=True)
            .select_related('category')
            .prefetch_related('images')
        )

        scent_pref = answers.get('scent_pref', '').strip().lower()
        raw_notes = answers.get('notes', [])
        if isinstance(raw_notes, str):
            raw_notes = [n.strip() for n in raw_notes.split(',') if n.strip()]
        notes = [n.lower() for n in raw_notes if n and 'no preference' not in n.lower()]
        vibe = answers.get('vibe', '').strip().lower()
        wear_time = answers.get('wear_time', '').strip().lower()
        strength = answers.get('strength', '').strip().lower()
        budget = answers.get('budget', '').strip()
        target_audience = answers.get('target_audience', '').strip().lower()

        scored = []
        for prod in products:
            score = 30  # Baseline viability score
            match_reasons = []
            fam = (prod.fragrance_family or '').lower()
            conc = (prod.concentration or '').lower()
            gender = (prod.gender or '').lower()
            name_lower = (prod.name or '').lower()
            desc_lower = (prod.description or '').lower()
            price = float(prod.effective_price if hasattr(prod, 'effective_price') else prod.price)

            # 1. Scent Preference / Family matching
            if scent_pref:
                if 'fresh' in scent_pref and fam in ('fresh', 'citrus'):
                    score += 40
                    match_reasons.append("Fresh & invigorating character")
                elif 'sweet' in scent_pref and fam in ('gourmand', 'citrus', 'floral'):
                    score += 40
                    match_reasons.append("Luscious sweet & fruit accords")
                elif 'floral' in scent_pref and fam == 'floral':
                    score += 40
                    match_reasons.append("Opulent floral bouquet")
                elif 'woody' in scent_pref and fam in ('woody', 'oud'):
                    score += 40
                    match_reasons.append("Noble wood accords")
                elif 'spicy' in scent_pref and fam in ('oriental', 'woody', 'oud', 'musky'):
                    score += 40
                    match_reasons.append("Warm sensual spices")

            # 2. Specific Notes Matching
            matched_notes = []
            for note in notes:
                if note in desc_lower or note in name_lower:
                    score += 20
                    matched_notes.append(note.title())
            if matched_notes:
                match_reasons.append(f"Notes of {', '.join(matched_notes[:2])}")

            # 3. Target Audience / Gender
            if target_audience:
                if target_audience in ('unisex', 'all') or gender == 'unisex':
                    score += 25
                elif target_audience == gender:
                    score += 30
                    match_reasons.append(f"Tailored for {prod.get_gender_display()}")
                else:
                    score -= 10

            # 4. Strength / Concentration
            if strength:
                if strength == 'light' and conc in ('edt', 'edc', 'eau_fraiche'):
                    score += 20
                    match_reasons.append("Subtle, airy sillage")
                elif strength == 'moderate' and conc == 'edp':
                    score += 20
                    match_reasons.append("Balanced Eau de Parfum longevity")
                elif strength == 'strong' and conc in ('parfum', 'edp'):
                    score += 20
                    match_reasons.append("Deep, long-lasting projection")

            # 5. Wear Time
            if wear_time:
                if wear_time == 'day' and fam in ('fresh', 'citrus', 'floral'):
                    score += 15
                elif wear_time == 'night' and fam in ('oud', 'woody', 'oriental', 'musky'):
                    score += 15
                elif wear_time == 'both':
                    score += 15

            # 6. Vibe
            if vibe:
                if vibe == 'everyday' and fam in ('fresh', 'citrus', 'woody'):
                    score += 15
                    match_reasons.append("Effortless daily signature")
                elif vibe == 'elegant' and conc in ('parfum', 'edp'):
                    score += 15
                    match_reasons.append("Refined regal sillage")
                elif vibe == 'romantic' and fam in ('floral', 'gourmand', 'musky'):
                    score += 15
                    match_reasons.append("Intimate, alluring trail")
                elif vibe in ('bold', 'mysterious') and fam in ('oud', 'oriental', 'woody'):
                    score += 15
                    match_reasons.append("Intense enigmatic profile")

            # 7. Budget Affinity
            if 'under' in budget.lower() or '1,000' in budget:
                if price <= 15000:
                    score += 15
            elif '2,500+' in budget:
                if price >= 20000:
                    score += 15

            # 8. Gifting Mode vs Personal Mode
            is_gifting = (purpose == 'gifting')
            if is_gifting:
                if prod.is_featured or conc == 'parfum':
                    score += 25
                    match_reasons.append("Artisanal flacon presentation")
                elif gender == 'unisex':
                    score += 15
                    match_reasons.append("Universally admired profile")

            # In-stock bonus
            if prod.stock > 0:
                score += 10

            # Normalise percentage between 78% and 99%
            computed_pct = min(99, max(78, int(60 + (score * 0.28))))

            primary_reason = match_reasons[0] if match_reasons else f"{prod.get_fragrance_family_display()} Olfactory Match"

            scored.append({
                'product': prod,
                'score': score,
                'match_percentage': computed_pct,
                'match_reason': primary_reason,
                'is_gifting': is_gifting,
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]