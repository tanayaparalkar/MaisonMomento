import re
import uuid
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.notifications.models import Notification
from .models import Customer, Wishlist
from .services import get_customer_from_user


def _is_ajax(request):
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or request.content_type == "application/json"
    )


def _safe_redirect_url(url, fallback="/"):
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return fallback


def customer_login(request):
    """
    Client authentication endpoint.
    Handles login from the client profile drawer and standalone requests.
    Supports email or username, remember-me session persistence, and AJAX responses.
    """
    if request.method != "POST":
        return redirect("home")

    identifier = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    remember_me = request.POST.get("remember_me") in ["on", "true", "1", True]
    next_url = _safe_redirect_url(request.POST.get("next"), fallback=request.META.get("HTTP_REFERER", "/"))

    if not identifier or not password:
        err_msg = "Please provide both your email and password."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    # Resolve user by email or username
    user = User.objects.filter(email__iexact=identifier).first()
    if not user:
        user = User.objects.filter(username__iexact=identifier).first()

    authenticated_user = None
    if user:
        authenticated_user = authenticate(request, username=user.username, password=password)

    if not authenticated_user:
        err_msg = "Invalid email or password. Please verify your credentials."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    login(request, authenticated_user)

    # Session persistence
    if remember_me:
        request.session.set_expiry(1209600)  # 14 days
    else:
        request.session.set_expiry(0)  # Browser session closure

    # Ensure linked customer record exists
    customer = get_customer_from_user(authenticated_user)

    success_msg = f"Welcome back, {customer.display_name}."
    messages.success(request, success_msg)

    if _is_ajax(request):
        return JsonResponse({
            "success": True,
            "redirect_url": next_url,
            "message": success_msg,
            "customer": {
                "name": customer.display_name,
                "email": customer.email,
                "initials": customer.initials,
            }
        })

    return redirect(next_url)


def customer_register(request):
    """
    Client registration endpoint.
    Creates a new Customer and Django User account, enforces uniqueness,
    validates passwords, and auto-logs the new client in.
    """
    if request.method != "POST":
        return redirect("home")

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    phone = request.POST.get("phone", "").strip()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
    next_url = _safe_redirect_url(request.POST.get("next"), fallback=request.META.get("HTTP_REFERER", "/account/"))

    # Validations
    if not first_name:
        err_msg = "Please enter your first name."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    if not email:
        err_msg = "Please provide a valid email address."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    try:
        validate_email(email)
    except ValidationError:
        err_msg = "Please enter a valid email address."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    if User.objects.filter(email__iexact=email).exists():
        err_msg = "An account with this email address already exists. Please sign in instead."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    if len(password) < 6:
        err_msg = "Password must be at least 6 characters long."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    if password != confirm_password:
        err_msg = "Passwords do not match. Please re-enter."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(next_url)

    # Generate a unique username
    base_username = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0])[:20]
    username = base_username or "client"
    if User.objects.filter(username__iexact=username).exists():
        username = f"{base_username}_{uuid.uuid4().hex[:6]}"

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    # Check if an existing Customer without a user exists with this email
    customer = Customer.objects.filter(email__iexact=email).first()
    if customer:
        customer.user = user
        customer.first_name = first_name
        customer.last_name = last_name
        if phone:
            customer.phone = phone
        customer.save()
    else:
        customer = Customer.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone
        )

    # Log in automatically
    login(request, user)
    request.session.set_expiry(1209600)  # 14 days default for new registration

    success_msg = f"Welcome to Maison Moménto, {first_name}."
    messages.success(request, success_msg)

    if _is_ajax(request):
        return JsonResponse({
            "success": True,
            "redirect_url": next_url,
            "message": success_msg,
            "customer": {
                "name": customer.display_name,
                "email": customer.email,
                "initials": customer.initials,
            }
        })

    return redirect(next_url)


def customer_logout(request):
    """
    Client logout handler.
    Redirects back to previous page or home cleanly.
    """
    logout(request)
    messages.success(request, "You have been signed out of Maison Moménto.")
    next_url = _safe_redirect_url(
        request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER"),
        fallback="/"
    )
    # If the user was on /account/, navigate them to home so they aren't stopped by the auth guard
    if "/account/" in next_url:
        next_url = "/"
    return redirect(next_url)


@login_required(login_url="home")
def account_profile(request):
    """
    Luxury Client Atelier / Account Profile page (/account/).
    Presents client details, circular avatar with photo upload, order history,
    curated wishlist summary, saved address, and password settings.
    """
    customer = get_customer_from_user(request.user)
    orders = customer.orders.all().order_by("-created_at")
    wishlist_items = customer.wishlist.select_related("product").all()[:12]

    context = {
        "customer": customer,
        "orders": orders,
        "orders_count": orders.count(),
        "wishlist_count": customer.wishlist.count(),
        "wishlist_items": wishlist_items,
    }
    return render(request, "customers/profile.html", context)


@login_required
@require_POST
def update_profile(request):
    """Update personal details (name, phone) on the Customer and User records."""
    customer = get_customer_from_user(request.user)
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    phone = request.POST.get("phone", "").strip()

    if not first_name:
        err_msg = "First name is required."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect("customers:profile")

    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.save(update_fields=["first_name", "last_name", "phone"])

    if customer.user:
        customer.user.first_name = first_name
        customer.user.last_name = last_name
        customer.user.save(update_fields=["first_name", "last_name"])

    msg = "Your personal details have been updated."
    messages.success(request, msg)

    if _is_ajax(request):
        return JsonResponse({"success": True, "message": msg, "display_name": customer.display_name})

    return redirect("customers:profile")


@login_required
@require_POST
def update_address(request):
    """Update delivery address details on the Customer record."""
    customer = get_customer_from_user(request.user)
    customer.street_address = request.POST.get("street_address", "").strip()
    customer.apartment = request.POST.get("apartment", "").strip()
    customer.city = request.POST.get("city", "").strip()
    customer.state = request.POST.get("state", "").strip()
    customer.postal_code = request.POST.get("postal_code", "").strip()
    customer.country = request.POST.get("country", "").strip() or "India"
    customer.save(update_fields=["street_address", "apartment", "city", "state", "postal_code", "country"])

    msg = "Your shipping address has been saved."
    messages.success(request, msg)

    if _is_ajax(request):
        return JsonResponse({
            "success": True,
            "message": msg,
            "formatted_address": customer.formatted_address
        })

    return redirect(reverse("customers:profile") + "#addresses")


@login_required
@require_POST
def upload_avatar(request):
    """Handle client avatar photo upload."""
    customer = get_customer_from_user(request.user)
    if "avatar" not in request.FILES:
        err_msg = "Please select an image file to upload."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect("customers:profile")

    avatar_file = request.FILES["avatar"]
    # Basic size check (5MB limit)
    if avatar_file.size > 5 * 1024 * 1024:
        err_msg = "Image size must be under 5MB."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect("customers:profile")

    customer.avatar = avatar_file
    customer.save(update_fields=["avatar"])

    msg = "Your profile picture has been updated."
    messages.success(request, msg)

    if _is_ajax(request):
        return JsonResponse({
            "success": True,
            "message": msg,
            "avatar_url": customer.avatar.url
        })

    return redirect("customers:profile")


@login_required
@require_POST
def change_password(request):
    """Change client account password."""
    current_password = request.POST.get("current_password", "")
    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    if not request.user.check_password(current_password):
        err_msg = "Your current password is incorrect."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(reverse("customers:profile") + "#settings")

    if len(new_password) < 6:
        err_msg = "New password must be at least 6 characters long."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(reverse("customers:profile") + "#settings")

    if new_password != confirm_password:
        err_msg = "New passwords do not match."
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": err_msg}, status=400)
        messages.error(request, err_msg)
        return redirect(reverse("customers:profile") + "#settings")

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)

    msg = "Your password has been changed successfully."
    messages.success(request, msg)

    if _is_ajax(request):
        return JsonResponse({"success": True, "message": msg})

    return redirect(reverse("customers:profile") + "#settings")


@login_required
def notifications(request):
    """Customer notifications page."""
    qs = Notification.objects.filter(target_type="customer", recipient=request.user)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "customers/notifications.html", {
        "page_obj": page_obj
    })


@login_required
def mark_notification_read(request, pk):
    """Mark a customer notification as read."""
    if request.method == "POST":
        notif = get_object_or_404(Notification, pk=pk, target_type="customer", recipient=request.user)
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["is_read", "read_at"])
    return redirect("customers:notifications")
