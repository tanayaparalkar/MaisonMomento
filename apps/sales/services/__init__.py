# Sales services package
#
# Extension points for future integrations:
#
#   Payment Provider  → apps/sales/services/payment.py
#   Email / Notifications → apps/sales/services/notifications.py
#   Order State Machine  → apps/sales/services/order_state.py
#   Inventory Reservation → apps/sales/services/inventory.py  (not yet created)
#   Coupon / Discount Engine → apps/sales/services/coupons.py  (not yet created)
#   Tax Calculation       → apps/sales/services/tax.py         (not yet created)
#   Shipment Tracking     → apps/sales/services/shipping.py    (not yet created)
#
# Each integration area has its own module.
# Adding a new provider means adding a new file here, NOT modifying checkout logic.
