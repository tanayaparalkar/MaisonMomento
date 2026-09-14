"""
apps/recommendations/services/__init__.py
==========================================
Public API of the recommendations services package.

Re-exports preserve backward compatibility with any existing code that
imports from ``apps.recommendations.services`` directly:

    from apps.recommendations.services import RecommendationLogger       # still works
    from apps.recommendations.services import get_storefront_recommendations  # still works
    from apps.recommendations.services import RecommendationService      # new canonical import
"""

from .logger import RecommendationLogger                          # noqa: F401
from .recommendation_service import RecommendationService         # noqa: F401


# ---------------------------------------------------------------------------
# Backward-compatibility shim
# ---------------------------------------------------------------------------
# Phase 7B introduced get_storefront_recommendations() as a module-level
# function. Phase 7C supersedes it with RecommendationService.get_homepage_context().
# The shim below keeps any existing callers working without modification.

def get_storefront_recommendations(visitor):
    """
    Backward-compatible alias for RecommendationService.get_homepage_context().

    .. deprecated::
        Use ``RecommendationService.get_homepage_context(visitor)`` directly.
        This shim will be removed in a future cleanup pass.
    """
    return RecommendationService.get_homepage_context(visitor)
