import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from apps.customers.models import Customer
from apps.customers.services import get_customer_from_user
from apps.catalog.models import Product
from .models import Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm
from .services.order_pipeline import place_order
from .services.notifications import send_order_confirmation
from .services.inventory import InsufficientStockError

logger = logging.getLogger(__name__)

@login_required
def cart_view(request):
    customer = get_customer_from_user(request.user)
    if customer:
        cart, _ = Cart.objects.get_or_create(customer=customer)
        items = cart.items.select_related('product', 'product__category').prefetch_related('product__images').all()
    else:
        cart = None
        items = []

    return render(request, "sales/cart.html", {
        "cart": cart,
        "items": items
    })


@require_POST
def cart_action(request):
    """
    Handle AJAX POST requests for cart modifications.
    Expected JSON body: {"action": "ADD"|"UPDATE"|"REMOVE", "product_id": int, "quantity": int}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "authenticated": False,
            "login_url": f"{reverse('login')}?next={request.META.get('HTTP_REFERER', '/')}"
        })

    customer = get_customer_from_user(request.user)
    if not customer:
        return JsonResponse({"error": "Invalid user"}, status=400)
        
    try:
        cart, _ = Cart.objects.get_or_create(customer=customer)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    try:
        data = json.loads(request.body)
        action = data.get("action")
        product_id = data.get("product_id")
        quantity = int(data.get("quantity", 1))
        
        if quantity < 0:
            quantity = 0

        product = get_object_or_404(Product, pk=product_id)

        if action == "ADD":
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, 
                product=product,
                defaults={"quantity": quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save(update_fields=['quantity', 'updated_at'])

        elif action == "UPDATE":
            if quantity > 0:
                cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
                cart_item.quantity = quantity
                cart_item.save(update_fields=['quantity', 'updated_at'])
            else:
                CartItem.objects.filter(cart=cart, product=product).delete()

        elif action == "REMOVE":
            CartItem.objects.filter(cart=cart, product=product).delete()

        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

        # Refresh cart for totals
        product_image_url = None
        if product.primary_image and product.primary_image.image:
            product_image_url = product.primary_image.image.url
        elif product.images.first() and product.images.first().image:
            product_image_url = product.images.first().image.url

        return JsonResponse({
            "authenticated": True,
            "cart_total_items": cart.total_items,
            "cart_subtotal": f"{cart.subtotal:.2f}",
            "product_id": product.id,
            "product_name": product.name,
            "product_brand": product.brand,
            "product_price": f"{product.effective_price:.2f}",
            "product_image": product_image_url,
            "checkout_url": reverse("sales:checkout"),
            "cart_url": reverse("sales:cart"),
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def checkout_view(request):
    customer = get_customer_from_user(request.user)
    if not customer:
        return redirect('sales:cart')
        
    try:
        cart = Cart.objects.get(customer=customer)
        items = cart.items.select_related('product', 'product__category').prefetch_related('product__images').all()
    except Cart.DoesNotExist:
        return redirect('sales:cart')

    if not items.exists():
        return render(request, "sales/checkout_empty.html")

    initial_data = {
        'first_name': customer.first_name,
        'last_name': customer.last_name,
        'email': customer.email,
        'phone': customer.phone,
    }

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(
                    customer=customer,
                    cart=cart,
                    form_data=form.cleaned_data,
                )
            except ValueError:
                logger.warning("Checkout attempted with empty cart: customer=%s", customer.pk)
                return redirect('sales:cart')
            except InsufficientStockError as e:
                logger.warning(
                    "Insufficient stock at checkout: customer=%s product=%s requested=%s available=%s",
                    customer.pk, e.product.pk, e.requested, e.available,
                )
                messages.error(
                    request,
                    f"Sorry, '{e.product.name}' only has {e.available} unit(s) in stock "
                    f"but your cart contains {e.requested}. Please update your cart."
                )
                return redirect('sales:cart')

            logger.info("Order created: #%s customer=%s total=%s", order.order_number, customer.pk, order.total)
            # Notification stub — harmless until email is configured
            send_order_confirmation(order)

            # PRG: redirect to confirmation page — prevents duplicate orders on refresh
            return redirect('sales:order_confirmation', order_number=order.order_number)

    else:
        form = CheckoutForm(initial=initial_data)

    context = {
        "form": form,
        "items": items,
        "cart_item_count": cart.total_items,
        "subtotal": f"{cart.subtotal:.2f}",
        "shipping_placeholder": "Calculated after order placement",
        "tax_placeholder": "Calculated during payment",
        "estimated_total": f"{cart.subtotal:.2f}",
    }
    return render(request, "sales/checkout.html", context)


@login_required
def order_confirmation(request, order_number):
    """
    Order confirmation page (GET only — reached via POST→Redirect→GET).
    Authenticated customers may only view their own orders.
    """
    customer = get_customer_from_user(request.user)
    if not customer:
        raise Http404

    order = get_object_or_404(
        Order.objects
        .select_related('customer')
        .prefetch_related('items__product', 'items__product__images'),
        order_number=order_number,
    )

    # Access control: reject if this order belongs to a different customer
    if order.customer_id != customer.pk:
        raise Http404

    return render(request, "sales/order_confirmation.html", {"order": order})


@login_required
def my_orders(request):
    """
    List all orders for the authenticated customer.
    """
    customer = get_customer_from_user(request.user)
    if not customer:
        return render(request, "sales/my_orders.html", {"orders": []})

    orders = (
        Order.objects
        .filter(customer=customer)
        .prefetch_related('items__product', 'items__product__images')
        .order_by("-created_at")
    )

    return render(request, "sales/my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    """
    Detail page for a specific order belonging to the authenticated customer.
    Includes a timeline and Buy Again options.
    """
    customer = get_customer_from_user(request.user)
    if not customer:
        raise Http404

    order = get_object_or_404(
        Order.objects
        .select_related('customer')
        .prefetch_related('items__product', 'items__product__category', 'items__product__images'),
        order_number=order_number,
    )

    # Access control: only the owner can view their order
    if order.customer_id != customer.pk:
        raise Http404

    # The timeline defines the typical positive flow
    timeline_steps = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("packed", "Packed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
    ]
    
    # Identify how far along the order is
    status_index = -1
    for i, (key, label) in enumerate(timeline_steps):
        if key == order.order_status:
            status_index = i
            break
            
    # Handle terminal failure states that aren't in the normal positive flow
    is_cancelled = order.order_status == "cancelled"
    is_refunded = order.order_status == "refunded"

    context = {
        "order": order,
        "timeline_steps": timeline_steps,
        "status_index": status_index,
        "is_cancelled": is_cancelled,
        "is_refunded": is_refunded,
    }
    return render(request, "sales/order_detail.html", context)
