"""
apps/recommendations/services/recommendation_service.py
=========================================================
High-level recommendation orchestration service.

This module is the single place that knows HOW recommendations are assembled
for each page context. Views call RecommendationService; they do not import
RecommendationEngine directly.

Architecture
------------

    View / Template
         │
         ▼
  RecommendationService          ← orchestration (this file)
         │
         ▼
  RecommendationEngine           ← pure ranking/retrieval logic (engine.py)
         │
         ▼
  Interaction / Product models   ← data layer

Extension points
----------------
Each method below documents where a future capability plugs in WITHOUT
requiring changes to the caller (the view).

  ML model
      Replace RecommendationEngine calls with an ML inference client.
      The service method signature and return type remain identical.

  Redis / Memcached cache
      Wrap each method body with a cache.get / cache.set using a key
      derived from visitor.session_id. The view is unaffected.

  Hybrid recommendations
      Blend two result sets (e.g. collaborative + content-based) inside
      the service method before returning. The view receives the same dict.

  Collaborative filtering
      Add a `collaborative_filter(visitor)` call alongside the existing
      `recommend_for_visitor(visitor)` call in get_homepage_context().
      Merge the results with a deduplication step here.

  Cold-start (new visitor)
      The existing trending_products() fallback already handles cold-start.
      To improve it, replace the fallback with curated editorial picks
      sourced from a CMS or admin flag.

  A/B testing
      Add an experiment_id parameter to each method. Route visitors to
      different ranking strategies based on the experiment flag, then log
      which variant was served alongside the Interaction event.
"""

from ..engine import RecommendationEngine


class RecommendationService:
    """
    Orchestrates recommendation retrieval for each page context.

    All methods return plain Python dicts or lists so that views can spread
    the result directly into the template context without further processing.
    """

    # ------------------------------------------------------------------ #
    # Product list / homepage                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_homepage_context(visitor):
        """
        Return the full recommendation payload for the product listing page.

        Visibility rules applied here:
        - ``trending`` always populated (cold-start safe via fallback).
        - ``recent`` only populated when the visitor has a view history.
        - ``recommended`` only populated when ``recent`` is non-empty;
          suppressed entirely when it would duplicate ``trending`` exactly
          (avoids showing the same row twice on the page).

        Parameters
        ----------
        visitor : tracking.VisitorSession | None

        Returns
        -------
        dict with keys:
            trending    : list[catalog.Product]
            recent      : list[catalog.Product]
            recommended : list[catalog.Product]

        Extension points
        ----------------
        Cache:
            key = f"homepage_recs:{visitor.session_id if visitor else 'anon'}"
            Return the cached dict if present; populate and store if not.

        ML model:
            Replace RecommendationEngine.recommend_for_visitor() with a
            call to an ML scoring endpoint, keeping the return type identical.

        Collaborative filtering:
            Call a separate collaborative_filter(visitor) method and merge
            results with the content-based set using a ranked union.
        """
        trending = list(RecommendationEngine.trending_products())
        recent   = list(RecommendationEngine.recently_viewed(visitor))

        if recent:
            recommended = list(RecommendationEngine.recommend_for_visitor(visitor))
            # Deduplication rule: suppress recommended if it is an exact
            # duplicate of trending (same products in the same order).
            if [p.id for p in recommended] == [p.id for p in trending]:
                recommended = []
        else:
            # Cold-start or new visitor: no personalised recommendations yet.
            recommended = []

        return {
            "trending":     trending,
            "recent":       recent,
            "recommended":  recommended,
        }

    # ------------------------------------------------------------------ #
    # Product detail page                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_similar_products(product, limit=6):
        """
        Return products to show in the "You may also like" section on the
        product detail page.

        Parameters
        ----------
        product : catalog.Product
        limit   : int

        Returns
        -------
        QuerySet[catalog.Product]
            Active products in the same category, excluding the current one.

        Extension points
        ----------------
        Content-based similarity:
            Replace the category filter with a cosine-similarity lookup over
            fragrance note vectors stored in a feature table or vector DB
            (pgvector, Pinecone, Weaviate).

        Hybrid:
            Blend category-based results with collaborative "users who viewed
            this also viewed" data, ranked by a combined score.

        Cache:
            key = f"similar:{product.pk}"  — short TTL (5–15 min) is fine
            since product catalogues change infrequently.
        """
        return RecommendationEngine.similar_products(product, limit=limit)

    # ------------------------------------------------------------------ #
    # Trending (standalone)                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_trending(limit=6):
        """
        Return globally trending products, ranked by total interaction count.

        Parameters
        ----------
        limit : int

        Returns
        -------
        QuerySet[catalog.Product]

        Extension points
        ----------------
        Time-windowed trending:
            Pass a ``since`` datetime to RecommendationEngine.trending_products()
            to weight recent interactions more heavily than older ones.

        Redis sorted set:
            Maintain an incrementing score in Redis on every interaction event
            (via RecommendationLogger). Replace this call with a Redis ZREVRANGE
            lookup for O(log N) retrieval with no DB query.
        """
        return RecommendationEngine.trending_products(limit=limit)

    # ------------------------------------------------------------------ #
    # Recently viewed (standalone)                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_recently_viewed(visitor, limit=6):
        """
        Return the visitor's most recently viewed products in reverse
        chronological order (most recent first), deduplicated.

        Parameters
        ----------
        visitor : tracking.VisitorSession | None
        limit   : int

        Returns
        -------
        list[catalog.Product]

        Extension points
        ----------------
        Authenticated user persistence:
            When the visitor logs in, merge their anonymous session history
            with any previously recorded history tied to their Customer record
            so that recently-viewed survives a browser change.

        Redis list:
            Replace the Interaction query with an LRANGE on a per-visitor
            Redis list maintained by RecommendationLogger for O(1) reads.
        """
        return RecommendationEngine.recently_viewed(visitor, limit=limit)
