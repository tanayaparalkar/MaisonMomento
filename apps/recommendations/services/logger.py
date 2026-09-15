"""
apps/recommendations/services/logger.py
=========================================
Interaction event logger.

Writes a single Interaction row for every meaningful visitor action
(view, wishlist add, cart add, recommendation click, purchase).

This module has no orchestration logic — it is a thin write-only wrapper
around the Interaction model.
"""

from ..models import Interaction


class RecommendationLogger:
    """
    Records visitor–product interaction events.

    Extension points
    ----------------
    Streaming analytics:
        Add a call to an event bus (Kafka, Pub/Sub, Kinesis) alongside
        the ORM write to feed real-time ML pipelines without blocking.

    Async logging:
        Replace the synchronous Interaction.objects.create() with a
        Celery task or Django background task to avoid adding DB latency
        to the request cycle on high-traffic product pages.
    """

    @staticmethod
    def log(visitor, product, event_type, metadata=None):
        """
        Create an Interaction record for a visitor–product event.

        Parameters
        ----------
        visitor : tracking.VisitorSession | None
        product : catalog.Product
        event_type : str
            One of the EVENT_CHOICES defined on the Interaction model:
            'view', 'search', 'wishlist', 'cart', 'purchase',
            'recommendation_click'.
        metadata : dict | None
            Arbitrary extra data (e.g. search query, referrer).
        """
        Interaction.objects.create(
            visitor=visitor,
            product=product,
            event_type=event_type,
            metadata=metadata or {},
        )
