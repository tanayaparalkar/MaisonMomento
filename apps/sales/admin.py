from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, Voucher


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "get_discount_display",
        "min_cart_value",
        "usage_display",
        "status_label",
        "valid_from",
        "valid_until",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "discount_type", "valid_from", "valid_until")
    search_fields = ("code", "description")
    list_editable = ("is_active",)
    readonly_fields = ("used_count", "created_at", "updated_at")
    fieldsets = (
        ("Privilege Details", {
            "fields": ("code", "description", "discount_type", "discount_value", "max_discount")
        }),
        ("Eligibility & Conditions", {
            "fields": ("min_cart_value", "specific_customer")
        }),
        ("Scheduling & Validity", {
            "fields": ("valid_from", "valid_until", "is_active")
        }),
        ("Usage & Limits", {
            "fields": ("max_uses", "used_count", "created_at", "updated_at")
        }),
    )
    actions = ["activate_vouchers", "deactivate_vouchers"]

    def usage_display(self, obj):
        if obj.max_uses:
            return f"{obj.used_count} / {obj.max_uses}"
        return f"{obj.used_count} / ∞"
    usage_display.short_description = "Redemptions"

    def activate_vouchers(self, request, queryset):
        queryset.update(is_active=True)
    activate_vouchers.short_description = "Activate selected vouchers"

    def deactivate_vouchers(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_vouchers.short_description = "Deactivate selected vouchers"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "email",
        "subtotal",
        "discount",
        "total",
        "payment_status",
        "order_status",
        "created_at",
    )
    list_filter = ("order_status", "payment_status", "created_at")
    search_fields = ("order_number", "customer_name", "email", "phone")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = [OrderItemInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "total_items", "subtotal", "created_at", "updated_at")
    search_fields = ("session_key", "user__email")
    inlines = [CartItemInline]
