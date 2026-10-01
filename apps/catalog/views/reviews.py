"""
apps/catalog/views/reviews.py
==============================
Handles submission and processing of customer reviews for products.
"""

import json
import logging
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.catalog.models import Product, Review
from apps.customers.models import Customer
from apps.sales.models import OrderItem

logger = logging.getLogger(__name__)


@require_POST
def submit_review(request, pk):
    """
    Handle customer review submission for a product.
    Supports both standard form POST and asynchronous JSON / AJAX requests.
    """
    product = get_object_or_404(Product, pk=pk, is_active=True)
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.POST.get("format") == "json"
        or request.content_type == "application/json"
    )

    data = request.POST
    if request.content_type == "application/json" and request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            data = request.POST

    raw_rating = data.get("rating")
    reviewer_name = str(data.get("reviewer_name", "")).strip()
    title = str(data.get("title", "")).strip()
    comment = str(data.get("comment", "")).strip()

    # Validation
    errors = []
    try:
        rating = int(raw_rating)
        if rating < 1 or rating > 5:
            errors.append("Please select a rating between 1 and 5 stars.")
    except (TypeError, ValueError):
        errors.append("A valid star rating (1–5) is required.")

    if not reviewer_name:
        errors.append("Please provide your name or display pseudonym.")

    if not comment:
        errors.append("Please share your olfactory review or impressions.")

    if errors:
        error_msg = " ".join(errors)
        if is_ajax:
            return JsonResponse({"success": False, "error": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect(f"/products/{product.pk}/#write-review-form")

    # Check verified purchase
    customer = None
    is_verified = False
    customer_email = request.user.email if (request.user.is_authenticated and request.user.email) else data.get("email", "").strip()

    if customer_email:
        customer = Customer.objects.filter(email__iexact=customer_email).first()

    if customer:
        is_verified = OrderItem.objects.filter(
            order__customer=customer,
            order__payment_status="paid",
            product=product,
        ).exists()
    elif customer_email:
        is_verified = OrderItem.objects.filter(
            order__email__iexact=customer_email,
            order__payment_status="paid",
            product=product,
        ).exists()

    # Create Review (approved by default for authentic luxury showcase)
    review = Review.objects.create(
        product=product,
        customer=customer,
        reviewer_name=reviewer_name,
        rating=rating,
        title=title,
        comment=comment,
        is_verified_purchase=is_verified,
        is_approved=True,
    )

    success_msg = "Thank you for sharing your olfactory impression. Your review has been published."

    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": success_msg,
            "review": {
                "id": review.id,
                "reviewer_name": review.reviewer_name,
                "rating": review.rating,
                "stars": review.stars_display,
                "title": review.title,
                "comment": review.comment,
                "is_verified_purchase": review.is_verified_purchase,
                "created_at": review.created_at.strftime("%B %d, %Y"),
            },
            "average_rating": product.average_rating,
            "review_count": product.review_count,
            "distribution": product.get_rating_distribution(),
        })

    messages.success(request, success_msg)
    return redirect(f"/products/{product.pk}/#customer-reviews")
