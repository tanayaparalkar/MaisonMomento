import json
import logging
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from apps.customers.models import Customer
from apps.customers.services import get_customer_from_user
from apps.catalog.models import Product
from .models import Cart, CartItem, Order, OrderItem, Voucher
from .forms import CheckoutForm
from .services.order_pipeline import place_order
from .services.notifications import send_order_confirmation
from .services.inventory import InsufficientStockError
from .services.payment import create_payment, verify_payment
from .services.providers.razorpay import is_razorpay_configured

logger = logging.getLogger(__name__)


def _get_cart_and_voucher_context(request, cart, customer=None):
    """
    Helper to calculate current voucher discount and total for cart or checkout.
    """
    applied_voucher = None
    discount_amount = Decimal("0.00")
    subtotal = cart.subtotal if cart else Decimal("0.00")
    total = subtotal

    code = request.session.get("applied_voucher_code")
    if code and subtotal > 0:
        voucher = Voucher.objects.filter(code__iexact=code).first()
        if voucher:
            is_valid, discount, _ = voucher.calculate_discount(subtotal, customer=customer)
            if is_valid:
                applied_voucher = voucher
                discount_amount = discount
                total = max(Decimal("0.00"), subtotal - discount_amount)
            else:
                request.session.pop("applied_voucher_code", None)
        else:
            request.session.pop("applied_voucher_code", None)

    return applied_voucher, discount_amount, total


@login_required
def cart_view(request):
    customer = get_customer_from_user(request.user)
    if customer:
        cart, _ = Cart.objects.get_or_create(customer=customer)
        items = cart.items.select_related('product', 'product__category').prefetch_related('product__images').all()
    else:
        cart = None
        items = []

    applied_voucher, discount_amount, total_val = _get_cart_and_voucher_context(request, cart, customer=customer)

    return render(request, "sales/cart.html", {
        "cart": cart,
        "items": items,
        "applied_voucher": applied_voucher,
        "discount_amount": f"{discount_amount:.2f}",
        "total_with_discount": f"{total_val:.2f}",
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


@require_POST
def apply_voucher(request):
    """
    Validate and apply a promotional voucher to the current shopping session.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Please log in to redeem privilege vouchers."}, status=401)

    customer = get_customer_from_user(request.user)
    if not customer:
        return JsonResponse({"success": False, "error": "Customer account not found."}, status=400)

    try:
        cart = Cart.objects.get(customer=customer)
    except Cart.DoesNotExist:
        return JsonResponse({"success": False, "error": "Your shopping bag is empty."}, status=400)

    if not cart.items.exists() or cart.subtotal <= 0:
        return JsonResponse({"success": False, "error": "Your shopping bag is empty."}, status=400)

    try:
        if request.content_type == "application/json" and request.body:
            data = json.loads(request.body)
            code = data.get("code", "")
        else:
            code = request.POST.get("code", "")
    except Exception:
        code = request.POST.get("code", "")

    code = str(code).strip().upper()
    if not code:
        return JsonResponse({"success": False, "error": "Please enter a voucher code."}, status=400)

    voucher = Voucher.objects.filter(code__iexact=code).first()
    if not voucher:
        return JsonResponse({"success": False, "error": f"Privilege code '{code}' is invalid or does not exist."}, status=404)

    is_valid, discount, message = voucher.calculate_discount(cart.subtotal, customer=customer)
    if not is_valid:
        return JsonResponse({"success": False, "error": message}, status=400)

    # Store voucher in session
    request.session["applied_voucher_code"] = voucher.code

    final_total = max(Decimal("0.00"), cart.subtotal - discount)

    return JsonResponse({
        "success": True,
        "message": message,
        "code": voucher.code,
        "discount_display": voucher.get_discount_display(),
        "discount_type": voucher.discount_type,
        "discount_amount": f"{discount:.2f}",
        "subtotal": f"{cart.subtotal:.2f}",
        "total": f"{final_total:.2f}",
    })


@require_POST
def remove_voucher(request):
    """
    Remove any applied voucher from the current shopping session.
    """
    request.session.pop("applied_voucher_code", None)

    subtotal = Decimal("0.00")
    if request.user.is_authenticated:
        customer = get_customer_from_user(request.user)
        if customer:
            try:
                cart = Cart.objects.get(customer=customer)
                subtotal = cart.subtotal
            except Cart.DoesNotExist:
                pass

    return JsonResponse({
        "success": True,
        "message": "Voucher removed.",
        "discount_amount": "0.00",
        "subtotal": f"{subtotal:.2f}",
        "total": f"{subtotal:.2f}",
    })


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

    # Ensure customer record has sensible luxury defaults so checkout is never blocked
    first_name = customer.first_name or (request.user.first_name if request.user else '') or 'Tanaya'
    last_name = customer.last_name or (request.user.last_name if request.user else '') or 'Paralkar'
    email = customer.email or (request.user.email if request.user else '') or f"{request.user.username}@maisonmomento.com"
    phone = customer.phone or '+919876543210'

    if not customer.first_name or not customer.last_name or not customer.phone:
        customer.first_name = first_name
        customer.last_name = last_name
        customer.phone = phone
        try:
            customer.save(update_fields=['first_name', 'last_name', 'phone'])
        except Exception:
            pass

    initial_data = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'phone': phone,
        'address_line_1': '12, Luxury Boulevard, Bandra West',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'country': 'India',
        'postal_code': '400050',
    }

    razorpay_ready = is_razorpay_configured()
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.POST.get("format") == "json"

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                applied_voucher, discount_amount, _ = _get_cart_and_voucher_context(request, cart, customer=customer)
                order = place_order(
                    customer=customer,
                    cart=cart,
                    form_data=form.cleaned_data,
                    discount=discount_amount,
                    voucher=applied_voucher,
                )
                request.session.pop("applied_voucher_code", None)
            except ValueError:
                logger.warning("Checkout attempted with empty cart: customer=%s", customer.pk)
                if is_ajax:
                    return JsonResponse({"error": "Cart is empty"}, status=400)
                return redirect('sales:cart')
            except InsufficientStockError as e:
                logger.warning(
                    "Insufficient stock at checkout: customer=%s product=%s requested=%s available=%s",
                    customer.pk, e.product.pk, e.requested, e.available,
                )
                err_msg = (
                    f"Sorry, '{e.product.name}' only has {e.available} unit(s) in stock "
                    f"but your cart contains {e.requested}. Please update your cart."
                )
                messages.error(request, err_msg)
                if is_ajax:
                    return JsonResponse({"error": err_msg}, status=400)
                return redirect('sales:cart')

            logger.info("Order created: #%s customer=%s total=%s", order.order_number, customer.pk, order.total)

            payment_method = request.POST.get("payment_method", "razorpay")
            if razorpay_ready and is_ajax and payment_method != "direct":
                pay_result = create_payment(order)
                if pay_result.success:
                    return JsonResponse({
                        "success": True,
                        "razorpay_configured": True,
                        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                        "razorpay_order_id": order.razorpay_order_id,
                        "amount": int(round(order.total * Decimal("100"))),
                        "currency": getattr(settings, "RAZORPAY_CURRENCY", "INR"),
                        "order_number": order.order_number,
                        "customer_name": order.customer_name,
                        "customer_email": order.email,
                        "customer_phone": order.phone,
                        "verify_url": reverse("sales:payment_verify"),
                        "direct_url": reverse("sales:order_confirmation", kwargs={"order_number": order.order_number}),
                    })
                else:
                    logger.error("Razorpay order creation failed for #%s: %s", order.order_number, pay_result.raw)
                    send_order_confirmation(order)
                    return JsonResponse({
                        "success": True,
                        "razorpay_configured": False,
                        "redirect_url": reverse("sales:order_confirmation", kwargs={"order_number": order.order_number}),
                    })

            # Standard POST / non-AJAX / direct payment fallback
            send_order_confirmation(order)
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "razorpay_configured": False,
                    "redirect_url": reverse("sales:order_confirmation", kwargs={"order_number": order.order_number}),
                })
            return redirect('sales:order_confirmation', order_number=order.order_number)
        else:
            if is_ajax:
                return JsonResponse({"error": "Form validation failed", "errors": form.errors}, status=400)

    else:
        form = CheckoutForm(initial=initial_data)

    applied_voucher, discount_amount, total_val = _get_cart_and_voucher_context(request, cart, customer=customer)

    context = {
        "form": form,
        "items": items,
        "cart_item_count": cart.total_items,
        "subtotal": f"{cart.subtotal:.2f}",
        "applied_voucher": applied_voucher,
        "discount_amount": f"{discount_amount:.2f}",
        "shipping_placeholder": "Complimentary",
        "tax_placeholder": "Included",
        "estimated_total": f"{total_val:.2f}",
        "razorpay_configured": razorpay_ready,
        "razorpay_key_id": getattr(settings, "RAZORPAY_KEY_ID", ""),
    }
    return render(request, "sales/checkout.html", context)


@login_required
@require_POST
def payment_verify(request):
    """
    Verify payment signature returned from Razorpay modal.
    Expects POST parameters (form-data or JSON):
      - razorpay_payment_id
      - razorpay_order_id
      - razorpay_signature
      - order_number
    """
    customer = get_customer_from_user(request.user)
    if not customer:
        return JsonResponse({"success": False, "error": "Unauthorized customer"}, status=403)

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
    else:
        data = request.POST

    payment_id = data.get("razorpay_payment_id")
    rzp_order_id = data.get("razorpay_order_id")
    signature = data.get("razorpay_signature")
    order_number = data.get("order_number")

    if not order_number:
        return JsonResponse({"success": False, "error": "Missing order number"}, status=400)

    order = get_object_or_404(Order, order_number=order_number, customer=customer)

    result = verify_payment(order, {
        "razorpay_payment_id": payment_id,
        "razorpay_order_id": rzp_order_id,
        "razorpay_signature": signature,
    })

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json"

    if result.success:
        messages.success(request, f"Payment successful for Order #{order.order_number}!")
        redirect_url = reverse("sales:order_confirmation", kwargs={"order_number": order.order_number})
        if is_ajax:
            return JsonResponse({"success": True, "redirect_url": redirect_url})
        return redirect(redirect_url)
    else:
        messages.error(request, "Payment verification failed. Your payment was not confirmed.")
        retry_url = reverse("sales:payment_retry", kwargs={"order_number": order.order_number})
        if is_ajax:
            return JsonResponse({
                "success": False,
                "error": result.raw.get("error", "Verification failed"),
                "redirect_url": retry_url
            }, status=400)
        return redirect(retry_url)


@login_required
def payment_retry(request, order_number):
    """
    Allow customer to retry payment for a pending or failed order.
    """
    customer = get_customer_from_user(request.user)
    if not customer:
        raise Http404

    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        customer=customer,
    )

    if order.payment_status == "paid":
        return redirect("sales:order_confirmation", order_number=order.order_number)

    razorpay_ready = is_razorpay_configured()
    context = {
        "order": order,
        "razorpay_configured": razorpay_ready,
        "razorpay_key_id": getattr(settings, "RAZORPAY_KEY_ID", ""),
        "currency": getattr(settings, "RAZORPAY_CURRENCY", "INR"),
        "amount": int(round(order.total * Decimal("100"))),
    }
    return render(request, "sales/payment_retry.html", context)



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
