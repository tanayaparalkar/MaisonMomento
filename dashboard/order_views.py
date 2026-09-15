from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from apps.sales.models import Order
from apps.sales.services.order_state import (
    mark_order_confirmed,
    mark_order_packed,
    mark_order_shipped,
    mark_order_delivered,
    mark_order_cancelled,
    mark_order_refunded,
    InvalidStateTransition
)

@staff_member_required
def orders(request):
    """
    List view for all orders with search, filters, and pagination.
    """
    orders_qs = Order.objects.select_related("customer").prefetch_related("items__product").order_by("-created_at")
    
    # Search
    search_query = request.GET.get("q", "")
    if search_query:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query)
        )
        
    # Filters
    status_filter = request.GET.get("status", "")
    if status_filter:
        orders_qs = orders_qs.filter(order_status=status_filter)
        
    payment_filter = request.GET.get("payment_status", "")
    if payment_filter:
        orders_qs = orders_qs.filter(payment_status=payment_filter)

    # Pagination
    paginator = Paginator(orders_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "dashboard/orders.html", {
        "orders": page_obj,  # Context expects 'orders'
        "search_query": search_query,
        "status_filter": status_filter,
        "payment_filter": payment_filter,
        "status_choices": Order.ORDER_STATUS_CHOICES,
        "payment_choices": Order.PAYMENT_STATUS_CHOICES,
    })


@staff_member_required
def order_detail(request, pk):
    """
    Detailed view for a specific order.
    """
    order = get_object_or_404(Order.objects.select_related("customer"), pk=pk)
    
    # Simple valid transitions map for UI rendering
    valid_transitions = []
    if order.order_status == "pending":
        valid_transitions.append(("confirmed", "Confirm Order"))
        valid_transitions.append(("cancelled", "Cancel Order"))
    elif order.order_status == "confirmed":
        valid_transitions.append(("packed", "Mark Packed"))
        valid_transitions.append(("cancelled", "Cancel Order"))
    elif order.order_status == "packed":
        valid_transitions.append(("shipped", "Mark Shipped"))
        valid_transitions.append(("cancelled", "Cancel Order"))
    elif order.order_status == "shipped":
        valid_transitions.append(("delivered", "Mark Delivered"))
        
    if order.payment_status == "paid" and order.order_status == "delivered":
        valid_transitions.append(("refunded", "Refund"))

    return render(request, "dashboard/order_detail.html", {
        "order": order,
        "valid_transitions": valid_transitions
    })


@staff_member_required
def order_transition(request, pk):
    """
    Strictly protected POST endpoint to transition an order's state.
    """
    if request.method != "POST":
        return redirect("dashboard:orders")
        
    order = get_object_or_404(Order, pk=pk)
    target_state = request.POST.get("target_state")
    
    try:
        if target_state == "confirmed":
            mark_order_confirmed(order)
        elif target_state == "packed":
            mark_order_packed(order)
        elif target_state == "shipped":
            tracking_ref = request.POST.get("tracking_reference")
            mark_order_shipped(order, tracking_reference=tracking_ref)
        elif target_state == "delivered":
            mark_order_delivered(order)
        elif target_state == "cancelled":
            mark_order_cancelled(order)
        elif target_state == "refunded":
            mark_order_refunded(order)
        else:
            messages.error(request, f"Unknown transition target: {target_state}")
            return redirect("dashboard:order_detail", pk=pk)
            
        messages.success(request, f"Order #{order.order_number} successfully marked as {target_state.title()}.")
    except InvalidStateTransition as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Failed to transition order: {e}")

    return redirect("dashboard:order_detail", pk=pk)
