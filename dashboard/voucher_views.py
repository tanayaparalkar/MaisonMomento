"""
dashboard/voucher_views.py
==========================
Administrative views for managing promotional privilege vouchers.
Features:
- Comprehensive voucher listing with metrics, filters, and search.
- Filter by active, scheduled, expired, deactivated, and discount types.
- Create, update, schedule, toggle status, and delete vouchers.
- Track real-time redemption counts and usage caps.
- Restrict to specific VIP patrons when desired.
"""

from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.sales.models import Voucher
from .decorators import staff_member_required
from .forms import VoucherForm


@staff_member_required
def vouchers(request):
    """
    List view for all promotional vouchers with filters (status, type), search,
    metrics breakdown, and bulk actions.
    """
    if request.method == "POST":
        action = request.POST.get("action")
        selected_ids = request.POST.getlist("selected_vouchers")

        if not action or not selected_ids:
            messages.warning(request, "Please select at least one voucher and an action.")
            return redirect("dashboard:vouchers")

        vouchers_qs = Voucher.objects.filter(id__in=selected_ids)
        count = vouchers_qs.count()

        try:
            with transaction.atomic():
                if action == "activate":
                    vouchers_qs.update(is_active=True)
                    messages.success(request, f"Successfully activated {count} voucher{'' if count == 1 else 's'}.")
                elif action == "deactivate":
                    vouchers_qs.update(is_active=False)
                    messages.success(request, f"Successfully deactivated {count} voucher{'' if count == 1 else 's'}.")
                elif action == "delete":
                    vouchers_qs.delete()
                    messages.success(request, f"Successfully removed {count} voucher{'' if count == 1 else 's'}.")
        except Exception as e:
            messages.error(request, f"Error processing bulk action: {str(e)}")

        return redirect("dashboard:vouchers")

    # Base QuerySet
    queryset = Voucher.objects.select_related("specific_customer").order_by("-created_at")
    now = timezone.now()

    # Search
    search_query = request.GET.get("q", "").strip()
    if search_query:
        queryset = queryset.filter(
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(specific_customer__first_name__icontains=search_query) |
            Q(specific_customer__last_name__icontains=search_query) |
            Q(specific_customer__email__icontains=search_query)
        )

    # Status Filter
    selected_status = request.GET.get("status", "").strip().lower()
    if selected_status == "active":
        queryset = queryset.filter(
            is_active=True,
            valid_from__lte=now
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=now)
        )
    elif selected_status == "expired":
        queryset = queryset.filter(
            valid_until__lt=now
        )
    elif selected_status == "scheduled":
        queryset = queryset.filter(
            valid_from__gt=now
        )
    elif selected_status == "deactivated":
        queryset = queryset.filter(
            is_active=False
        )

    # Discount Type Filter
    selected_type = request.GET.get("type", "").strip()
    if selected_type in ["percentage", "flat"]:
        queryset = queryset.filter(discount_type=selected_type)

    # Metrics
    all_vouchers = Voucher.objects.all()
    total_count = all_vouchers.count()
    active_count = all_vouchers.filter(
        is_active=True,
        valid_from__lte=now
    ).filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=now)
    ).count()
    expired_count = all_vouchers.filter(valid_until__lt=now).count()
    total_redemptions = all_vouchers.aggregate(total=Sum("used_count"))["total"] or 0

    # Pagination
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "vouchers": page_obj.object_list,
        "total_count": total_count,
        "active_count": active_count,
        "expired_count": expired_count,
        "total_redemptions": total_redemptions,
        "search_query": search_query,
        "selected_status": selected_status,
        "selected_type": selected_type,
        "now": now,
    }
    return render(request, "dashboard/vouchers.html", context)


@staff_member_required
def voucher_create(request):
    """
    Create a new promotional privilege voucher with custom rules, scheduling,
    and discount definitions.
    """
    if request.method == "POST":
        form = VoucherForm(request.POST)
        if form.is_valid():
            voucher = form.save()
            messages.success(request, f"Privilege voucher '{voucher.code}' has been created successfully.")
            return redirect("dashboard:vouchers")
    else:
        form = VoucherForm()

    context = {
        "form": form,
        "action": "Create",
        "title": "Create Privilege Voucher",
    }
    return render(request, "dashboard/voucher_form.html", context)


@staff_member_required
def voucher_edit(request, pk):
    """
    Modify an existing voucher's parameters, limits, validity, or customer assignments.
    """
    voucher = get_object_or_404(Voucher, pk=pk)

    if request.method == "POST":
        form = VoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            form.save()
            messages.success(request, f"Privilege voucher '{voucher.code}' updated successfully.")
            return redirect("dashboard:vouchers")
    else:
        form = VoucherForm(instance=voucher)

    context = {
        "form": form,
        "voucher": voucher,
        "action": "Edit",
        "title": f"Edit Voucher: {voucher.code}",
    }
    return render(request, "dashboard/voucher_form.html", context)


@staff_member_required
def voucher_toggle(request, pk):
    """
    Quickly toggle a voucher between Active and Deactivated.
    """
    voucher = get_object_or_404(Voucher, pk=pk)
    voucher.is_active = not voucher.is_active
    voucher.save(update_fields=["is_active", "updated_at"])

    state_label = "activated" if voucher.is_active else "deactivated"
    messages.success(request, f"Privilege voucher '{voucher.code}' has been {state_label}.")

    redirect_url = request.META.get("HTTP_REFERER") or "dashboard:vouchers"
    return redirect(redirect_url)


@staff_member_required
def voucher_delete(request, pk):
    """
    Delete a voucher. Provides confirmation and warns if it has active redemptions.
    """
    voucher = get_object_or_404(Voucher, pk=pk)

    if request.method == "POST":
        code = voucher.code
        voucher.delete()
        messages.success(request, f"Privilege voucher '{code}' has been permanently deleted.")
        return redirect("dashboard:vouchers")

    context = {
        "voucher": voucher,
    }
    return render(request, "dashboard/voucher_confirm_delete.html", context)
