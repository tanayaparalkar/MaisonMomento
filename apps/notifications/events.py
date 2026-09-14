import logging
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)

# Lightweight in-memory event dispatcher
_subscribers: Dict[str, List[Callable]] = {}

def subscribe(event_name: str):
    """
    Decorator to subscribe a function to a domain event.
    Usage:
        @subscribe('order.created')
        def handle_order_created(event_data):
            pass
    """
    def decorator(func: Callable):
        if event_name not in _subscribers:
            _subscribers[event_name] = []
        if func not in _subscribers[event_name]:
            _subscribers[event_name].append(func)
        return func
    return decorator

def publish_event(event_name: str, **kwargs: Any):
    """
    Publish a domain event to all subscribers synchronously.
    This prepares the system for future background workers without coupling logic.
    """
    subscribers = _subscribers.get(event_name, [])
    logger.debug(f"Event published: {event_name} with {len(subscribers)} subscribers")
    
    for func in subscribers:
        try:
            func(kwargs)
        except Exception as e:
            logger.error(f"Error in subscriber {func.__name__} for event {event_name}: {e}")
