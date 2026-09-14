import logging
from django.conf import settings
from django.db import transaction
from django.db.models import F

from apps.catalog.models import Product
from apps.inventory.models import StockAdjustment

logger = logging.getLogger(__name__)


class InsufficientStockError(ValueError):
    """
    Raised when a product does not have enough stock to fulfil a quantity.
    """

    def __init__(self, product, requested, available):
        self.product = product
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for '{product.name}': "
            f"requested {requested}, available {available}."
        )


def check_stock(cart_items):
    """
    Verify that every cart item can be fulfilled from current stock.
    """
    for cart_item in cart_items:
        product = cart_item.product
        if product.stock < cart_item.quantity:
            raise InsufficientStockError(
                product=product,
                requested=cart_item.quantity,
                available=product.stock,
            )


def deduct_inventory(order_items):
    """
    Deduct stock for every OrderItem.
    """
    product_ids = [item.product_id for item in order_items]

    locked_products = {
        p.pk: p
        for p in Product.objects.select_for_update().filter(pk__in=product_ids).order_by('pk')
    }

    for item in order_items:
        product = locked_products[item.product_id]
        if product.stock < item.quantity:
            raise InsufficientStockError(
                product=product,
                requested=item.quantity,
                available=product.stock,
            )

        Product.objects.filter(pk=product.pk).update(stock=F('stock') - item.quantity)
        
        actual_new_stock = product.stock - item.quantity
        
        # Log the stock adjustment
        StockAdjustment.objects.create(
            product=product,
            quantity=-item.quantity,
            previous_stock=product.stock,
            new_stock=actual_new_stock,
            adjustment_type="decrease",
            reason="Order fulfillment",
            admin_user=None, # System action
        )

        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        if actual_new_stock == 0:
            from apps.notifications.events import publish_event
            publish_event('inventory.out_of_stock', product=product)
        elif actual_new_stock <= threshold:
            from apps.notifications.events import publish_event
            publish_event('inventory.low_stock', product=product, stock=actual_new_stock)

        logger.info(
            "Stock deducted: product=%s sku=%s qty=%s remaining=%s",
            product.pk,
            product.sku,
            item.quantity,
            actual_new_stock,
        )


def get_inventory_summary():
    """
    Return a summary dict of inventory health for dashboard widgets.
    """
    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)

    total_products      = Product.objects.filter(is_active=True).count()
    in_stock_count      = Product.objects.filter(is_active=True, stock__gt=threshold).count()
    low_stock_products  = (
        Product.objects
        .filter(is_active=True, stock__gt=0, stock__lte=threshold)
        .select_related("category")
        .order_by("stock")
    )
    out_of_stock_products = (
        Product.objects
        .filter(is_active=True, stock=0)
        .select_related("category")
    )

    low_stock_count     = low_stock_products.count()
    out_of_stock_count  = out_of_stock_products.count()

    return {
        "threshold":              threshold,
        "total_products":         total_products,
        "in_stock_count":         in_stock_count,
        "low_stock_count":        low_stock_count,
        "out_of_stock_count":     out_of_stock_count,
        "low_stock_products":     low_stock_products,
        "out_of_stock_products":  out_of_stock_products,
    }

@transaction.atomic
def adjust_stock(product, quantity, adjustment_type, reason="", user=None):
    """
    Manually adjust inventory for a specific product.
    Prevents negative inventory.
    Records a StockAdjustment entry.
    """
    if quantity == 0:
        return product

    locked_product = Product.objects.select_for_update().get(pk=product.pk)
    previous_stock = locked_product.stock
    new_stock = previous_stock + quantity

    if new_stock < 0:
        raise InsufficientStockError(
            product=locked_product,
            requested=abs(quantity),
            available=previous_stock,
        )

    # Perform the update
    Product.objects.filter(pk=locked_product.pk).update(stock=F('stock') + quantity)
    
    # Refresh from DB to ensure new_stock is exactly accurate for the log
    locked_product.refresh_from_db(fields=['stock'])
    actual_new_stock = locked_product.stock

    StockAdjustment.objects.create(
        product=locked_product,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=actual_new_stock,
        adjustment_type=adjustment_type,
        reason=reason,
        admin_user=user,
    )

    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if actual_new_stock == 0:
        from apps.notifications.events import publish_event
        publish_event('inventory.out_of_stock', product=locked_product)
    elif actual_new_stock <= threshold and previous_stock > threshold:
        # Only notify if we just crossed the threshold to avoid spam
        from apps.notifications.events import publish_event
        publish_event('inventory.low_stock', product=locked_product, stock=actual_new_stock)

    return locked_product
