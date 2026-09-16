from django.shortcuts import render, redirect, get_object_or_404
from .decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction

from apps.catalog.models import Product
from apps.inventory.models import StockAdjustment
from apps.inventory.services import adjust_stock

@staff_member_required
def adjust_stock_action(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == "POST":
        adjustment_type = request.POST.get("adjustment_type")
        quantity = request.POST.get("quantity", 0)
        reason = request.POST.get("reason", "")
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
                
            if adjustment_type in ["decrease", "damaged"]:
                if product.stock < quantity:
                    raise ValueError(f"Cannot decrease by {quantity}. Current stock is {product.stock}.")
                quantity = -quantity
                
            with transaction.atomic():
                adjust_stock(
                    product=product,
                    quantity=quantity,
                    adjustment_type=adjustment_type,
                    reason=reason,
                    user=request.user
                )
                
            messages.success(request, f"Successfully adjusted stock for {product.name}.")
            next_url = request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("dashboard:products")
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Failed to adjust stock: {str(e)}")
            
    return render(request, "dashboard/adjust_stock.html", {"product": product})


@staff_member_required
def stock_history(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    history_qs = StockAdjustment.objects.filter(product=product).order_by("-created_at")
    
    paginator = Paginator(history_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "dashboard/stock_history.html", {
        "product": product,
        "page_obj": page_obj
    })
