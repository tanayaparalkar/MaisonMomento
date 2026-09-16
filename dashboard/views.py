"""
dashboard/views.py
====================
Main dashboard view focusing on operational metrics, revenue tracking,
and system health. Other concerns (products, orders, exports) have been 
moved to dedicated view modules to prevent oversized views.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .decorators import staff_member_required
from django.shortcuts import render

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.sales.models import Order
from apps.inventory.models import StockAdjustment
from apps.inventory.services import get_inventory_summary
from apps.recommendations.engine import RecommendationEngine
from apps.recommendations.models import Interaction
from apps.tracking.models import VisitorSession

logger = logging.getLogger(__name__)


@staff_member_required
def dashboard(request):
    """
    Main dashboard — metrics, orders, top products, dynamic notifications,
    and recommendation health. Supports date filtering.
    """
    now = timezone.now()
    
    # Date Filtering logic
    date_filter = request.GET.get('date_range', 'last_30_days')
    
    if date_filter == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'last_7_days':
        start_date = now - timedelta(days=7)
    elif date_filter == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # 'last_30_days' is default
        start_date = now - timedelta(days=30)
        
    date_qs_kwargs = {'created_at__gte': start_date}

    # 1. Revenue Aggregation
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    revenue_today = Order.objects.filter(payment_status='paid', created_at__gte=today_start).aggregate(t=Sum('total'))['t'] or 0
    revenue_weekly = Order.objects.filter(payment_status='paid', created_at__gte=week_start).aggregate(t=Sum('total'))['t'] or 0
    revenue_monthly = Order.objects.filter(payment_status='paid', created_at__gte=month_start).aggregate(t=Sum('total'))['t'] or 0

    # Filtered Revenue (for the selected date range)
    revenue_filtered = Order.objects.filter(payment_status='paid', **date_qs_kwargs).aggregate(t=Sum('total'))['t'] or 0

    # 2. Orders Data (Filtered by date_range)
    base_orders = Order.objects.filter(**date_qs_kwargs)
    
    pending_orders_count = base_orders.filter(order_status="pending").count()
    awaiting_packing_count = base_orders.filter(order_status="confirmed").count()
    shipped_today_count = Order.objects.filter(order_status="shipped", updated_at__gte=today_start).count()
    delivered_today_count = Order.objects.filter(order_status="delivered", updated_at__gte=today_start).count()

    recent_orders = (
        Order.objects
        .select_related("customer")
        .prefetch_related("items")
        .order_by("-created_at")[:10]
    )

    order_status_counts = {}
    for status, label in Order.ORDER_STATUS_CHOICES:
        order_status_counts[label] = base_orders.filter(order_status=status).count()

    recent_customers = Customer.objects.order_by("-created_at")[:8]
    
    recent_inventory_activity = (
        StockAdjustment.objects
        .select_related("product", "admin_user")
        .order_by("-created_at")[:10]
    )

    # 3. Top Selling Products (Filtered by date_range)
    top_products = (
        Product.objects.filter(order_items__order__created_at__gte=start_date)
        .annotate(total_sold=Sum('order_items__quantity'))
        .order_by('-total_sold')[:5]
    )

    # 4. Recommendation Health
    engine_status = False
    trending_availability = False
    try:
        trending = list(RecommendationEngine.trending_products(limit=1))
        engine_status = True
        trending_availability = len(trending) > 0
    except Exception as e:
        logger.error("RecommendationEngine check failed: %s", e)

    health = {
        "engine_status": engine_status,
        "visitor_tracking_status": VisitorSession.objects.exists(),
        "interaction_logging_count": Interaction.objects.filter(created_at__gte=today_start).count(),
        "trending_availability": trending_availability,
        "personalization_status": VisitorSession.objects.filter(user__isnull=False).exists(),
        "recs_today": Interaction.objects.filter(event_type="recommendation_click", created_at__gte=today_start).count(),
        "last_rec_time": getattr(Interaction.objects.filter(event_type="recommendation_click").order_by("-created_at").first(), 'created_at', None)
    }

    # 5. Inventory & Notifications
    inventory = get_inventory_summary()
    from apps.notifications.models import Notification
    
    notifications_qs = Notification.objects.filter(
        target_type='admin',
        is_read=False
    ).order_by('-created_at')[:5]
    
    notifications = []
    for n in notifications_qs:
        icon = "ℹ️"
        if n.severity == "success": icon = "✅"
        elif n.severity == "warning": icon = "⚠️"
        elif n.severity == "error": icon = "❌"
        
        notifications.append({
            "severity": n.severity,
            "icon": icon,
            "title": n.title,
            "description": n.message,
            "url": n.url or "",
            "time": n.created_at,
        })

    return render(request, "dashboard/dashboard.html", {
        "date_filter": date_filter,
        
        "revenue_today": revenue_today,
        "revenue_weekly": revenue_weekly,
        "revenue_monthly": revenue_monthly,
        "revenue_filtered": revenue_filtered,
        
        "inventory": inventory,
        "recent_orders": recent_orders,
        "recent_customers": recent_customers,
        "recent_inventory_activity": recent_inventory_activity,
        "order_status_counts": order_status_counts,
        
        "pending_orders_count": pending_orders_count,
        "awaiting_packing_count": awaiting_packing_count,
        "shipped_today_count": shipped_today_count,
        "delivered_today_count": delivered_today_count,
        "top_products": top_products,
        
        "health": health,
        "notifications": notifications,
    })


@staff_member_required
def insights(request):
    """Analytics and Charts for Insights page."""
    # We can pass dummy data here for now, or just render the template since JS is hardcoded, 
    # but let's pass real data later if needed. For now, JS expects elements with IDs `#analyticsChart` and `#pieChart`.
    return render(request, "dashboard/insights.html")

@staff_member_required
def inventory(request):
    """Dedicated inventory page with full low-stock and out-of-stock listings."""
    summary = get_inventory_summary()
    return render(request, "dashboard/inventory.html", {"inventory": summary})


@staff_member_required
def clients(request):
    customers_qs = Customer.objects.order_by("-created_at")
    return render(request, "dashboard/clients.html", {"customers": customers_qs})


@staff_member_required
def recommendations(request):
    return render(request, "dashboard/recommendations.html")


@staff_member_required
def settings(request):
    return render(request, "dashboard/settings.html")