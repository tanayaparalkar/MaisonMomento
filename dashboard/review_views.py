"""
dashboard/review_views.py
==========================
Staff views for managing customer reviews and ratings.
Features:
- View all reviews with filtering by product, rating, and approval status.
- Search across reviewer, title, content, and fragrance name.
- Approve / reject reviews (individually or in bulk).
- Edit review content and metadata.
- Delete inappropriate reviews.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalog.models import Product, Review
from .decorators import staff_member_required


@staff_member_required
def reviews(request):
    """
    List view for all customer reviews with product and rating filters, search,
    approval toggling, and bulk operations.
    """
    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected_reviews")

        if not action or not selected_ids:
            messages.warning(request, "Please select at least one review and an action.")
            return redirect("dashboard:reviews")

        reviews_qs = Review.objects.filter(id__in=selected_ids)
        count = reviews_qs.count()

        try:
            with transaction.atomic():
                if action == "approve":
                    reviews_qs.update(is_approved=True)
                    messages.success(request, f"Successfully approved {count} review{'' if count == 1 else 's'}.")
                elif action == "reject":
                    reviews_qs.update(is_approved=False)
                    messages.success(request, f"Successfully rejected / hidden {count} review{'' if count == 1 else 's'}.")
                elif action == "delete":
                    reviews_qs.delete()
                    messages.success(request, f"Successfully deleted {count} review{'' if count == 1 else 's'}.")
        except Exception as e:
            messages.error(request, f"Error processing bulk action: {str(e)}")

        return redirect("dashboard:reviews")

    # Base QuerySet
    queryset = Review.objects.select_related("product", "customer").order_by("-created_at")

    # Metrics
    total_reviews_count = Review.objects.count()
    approved_count = Review.objects.filter(is_approved=True).count()
    pending_count = Review.objects.filter(is_approved=False).count()

    # Filter by Product
    product_id = request.GET.get("product")
    if product_id and product_id.isdigit():
        queryset = queryset.filter(product_id=int(product_id))

    # Filter by Rating
    rating_val = request.GET.get("rating")
    if rating_val and rating_val.isdigit():
        queryset = queryset.filter(rating=int(rating_val))

    # Filter by Approval Status
    status_filter = request.GET.get("status")
    if status_filter == "approved":
        queryset = queryset.filter(is_approved=True)
    elif status_filter == "pending":
        queryset = queryset.filter(is_approved=False)

    # Search Query
    search_query = request.GET.get("q", "").strip()
    if search_query:
        queryset = queryset.filter(
            Q(reviewer_name__icontains=search_query)
            | Q(title__icontains=search_query)
            | Q(comment__icontains=search_query)
            | Q(product__name__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    all_products = Product.objects.filter(is_active=True).order_by("name")

    context = {
        "reviews": page_obj,
        "page_obj": page_obj,
        "products": all_products,
        "selected_product": int(product_id) if (product_id and product_id.isdigit()) else None,
        "selected_rating": int(rating_val) if (rating_val and rating_val.isdigit()) else None,
        "selected_status": status_filter or "",
        "search_query": search_query,
        "total_count": total_reviews_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
    }

    return render(request, "dashboard/reviews.html", context)


@staff_member_required
def review_toggle_approval(request, pk):
    """
    Toggle approval status of a single review.
    """
    review = get_object_or_404(Review, pk=pk)
    review.is_approved = not review.is_approved
    review.save(update_fields=["is_approved", "updated_at"])

    status_label = "approved and visible" if review.is_approved else "rejected and hidden"
    messages.success(request, f"Review #{review.pk} by {review.reviewer_name} is now {status_label}.")

    # Redirect back to referring page or dashboard reviews
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return redirect(referer)
    return redirect("dashboard:reviews")


@staff_member_required
def review_edit(request, pk):
    """
    Edit review details, rating, or text.
    """
    review = get_object_or_404(Review, pk=pk)

    if request.method == "POST":
        reviewer_name = request.POST.get("reviewer_name", "").strip()
        raw_rating = request.POST.get("rating")
        title = request.POST.get("title", "").strip()
        comment = request.POST.get("comment", "").strip()
        is_approved = request.POST.get("is_approved") == "on"
        is_verified_purchase = request.POST.get("is_verified_purchase") == "on"

        errors = []
        try:
            rating = int(raw_rating)
            if rating < 1 or rating > 5:
                errors.append("Rating must be between 1 and 5.")
        except (TypeError, ValueError):
            errors.append("Valid rating between 1 and 5 is required.")

        if not reviewer_name:
            errors.append("Reviewer display name cannot be blank.")
        if not comment:
            errors.append("Review text cannot be blank.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            review.reviewer_name = reviewer_name
            review.rating = rating
            review.title = title
            review.comment = comment
            review.is_approved = is_approved
            review.is_verified_purchase = is_verified_purchase
            review.save()

            messages.success(request, f"Review #{review.pk} updated successfully.")
            return redirect("dashboard:reviews")

    context = {
        "review": review,
    }
    return render(request, "dashboard/review_edit.html", context)


@staff_member_required
def review_delete(request, pk):
    """
    Permanently delete an inappropriate or spam review.
    """
    review = get_object_or_404(Review, pk=pk)

    if request.method == "POST" or request.GET.get("confirm") == "yes":
        review_pk = review.pk
        reviewer = review.reviewer_name
        product_name = review.product.name
        review.delete()
        messages.success(request, f"Review #{review_pk} by {reviewer} for {product_name} was deleted.")
        return redirect("dashboard:reviews")

    context = {
        "review": review,
    }
    return render(request, "dashboard/review_confirm_delete.html", context)
