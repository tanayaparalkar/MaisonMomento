"""
apps/sales/services/order_pipeline.py
======================================
Core order creation service.

This module is the single place that knows how to turn a validated
CheckoutForm + Cart into a persisted Order. The checkout view delegates
to this function — it does NOT build orders itself.

Extension points
----------------
- Future payment step: call after place_order() returns, before redirecting.
- Coupon application: apply discounts to the Order before recalculate_totals().
- Tax calculation: set order.tax before recalculate_totals().
- Inventory reservation (pre-payment): use inventory.reserve_stock() instead
  of the hard check_stock() call below; release on payment failure.
"""

from django.db import transaction

from apps.sales.models import Cart, Order, OrderItem
from apps.sales.services.inventory import check_stock, deduct_inventory, InsufficientStockError


def place_order(customer, cart, form_data):
    """
    Create a single Order from a validated checkout form and a Cart.

    Parameters
    ----------
    customer : customers.Customer
        The authenticated customer placing the order.
    cart : sales.Cart
        The customer's active cart. Must not be empty.
    form_data : dict
        ``CheckoutForm.cleaned_data`` — all fields already validated.

    Returns
    -------
    sales.Order
        The newly persisted, fully totalled Order.

    Raises
    ------
    ValueError
        If the cart is empty at the moment of order creation.
    InsufficientStockError
        If any product does not have enough stock to fulfil the order.
        The entire transaction rolls back; the cart is untouched.
    """
    # Assemble a human-readable shipping address
    address_parts = [form_data["address_line_1"]]
    if form_data.get("address_line_2"):
        address_parts.append(form_data["address_line_2"])
    address_parts.append(
        f"{form_data['city']}, {form_data['state']} {form_data['postal_code']}"
    )
    address_parts.append(form_data["country"])
    shipping_address = "\n".join(address_parts)

    with transaction.atomic():
        # ------------------------------------------------------------------ #
        # 1. Guard: re-check cart inside the atomic block to prevent a race   #
        #    condition between two simultaneous checkout submissions.          #
        # ------------------------------------------------------------------ #
        cart_items = list(
            cart.items.select_related("product").select_for_update()
        )
        if not cart_items:
            raise ValueError("Cart is empty — cannot create order.")

        # ------------------------------------------------------------------ #
        # 2. Stock availability check (pre-order)                             #
        #    Raises InsufficientStockError if any item cannot be fulfilled.   #
        #    Transaction rolls back; cart is untouched.                       #
        # ------------------------------------------------------------------ #
        check_stock(cart_items)

        # ------------------------------------------------------------------ #
        # 3. Create the Order header                                           #
        # ------------------------------------------------------------------ #
        order = Order.objects.create(
            customer=customer,
            customer_name=f"{form_data['first_name']} {form_data['last_name']}".strip(),
            email=form_data["email"],
            phone=form_data["phone"],
            shipping_address=shipping_address,
            notes=form_data.get("delivery_notes", ""),
        )

        # ------------------------------------------------------------------ #
        # 4. Snapshot cart items → OrderItems                                 #
        #    unit_price is locked at effective_price at the moment of order.  #
        # ------------------------------------------------------------------ #
        order_items = []
        for cart_item in cart_items:
            oi = OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.effective_price,
            )
            order_items.append(oi)

        # ------------------------------------------------------------------ #
        # 5. Deduct inventory (inside the same atomic block)                  #
        #    Uses select_for_update + F() — atomic, no race conditions.       #
        #    Raises InsufficientStockError on concurrent stock exhaustion.     #
        # ------------------------------------------------------------------ #
        deduct_inventory(order_items)

        # ------------------------------------------------------------------ #
        # 6. Calculate totals via the canonical model method                  #
        #    Extension point: apply coupons / tax BEFORE this call.           #
        # ------------------------------------------------------------------ #
        order.recalculate_totals()

        # ------------------------------------------------------------------ #
        # 7. Clear cart ONLY after a fully successful commit                  #
        # ------------------------------------------------------------------ #
        cart.items.all().delete()

    return order
