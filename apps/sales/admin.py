from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]
    fields = ["product", "quantity", "unit_price", "subtotal"]
    readonly_fields = ["subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "customer_name",
        "phone",
        "formatted_total",
        "payment_status_badge",
        "order_status_badge",
        "created_at",
    ]
    list_display_links = ["order_number", "customer_name"]
    list_filter = ["order_status", "payment_status", "created_at"]
    search_fields = ["order_number", "customer_name", "email", "phone"]
    ordering = ["-created_at"]
    readonly_fields = ["order_number", "created_at", "updated_at", "subtotal", "total"]
    inlines = [OrderItemInline]

    fieldsets = (
        ("Order Identification", {
            "fields": (("order_number", "created_at"), ("order_status", "payment_status"))
        }),
        ("Customer & Delivery", {
            "fields": (("customer", "customer_name"), ("email", "phone"), "shipping_address", "notes")
        }),
        ("Financial Breakdown", {
            "fields": (("subtotal", "discount"), ("shipping_cost", "total"))
        }),
    )

    actions = [
        "mark_confirmed",
        "mark_processing",
        "mark_shipped",
        "mark_delivered",
        "mark_cancelled",
        "mark_paid",
    ]

    def formatted_total(self, obj):
        return format_html('<strong style="font-family: Courier Prime, monospace;">₹{}</strong>', f"{obj.total:,.2f}")

    formatted_total.short_description = "Total (₹)"
    formatted_total.admin_order_field = "total"

    def payment_status_badge(self, obj):
        colors = {
            "paid": ("#264e36", "#eaf2ed", "#9cbda9"),
            "pending": ("#7a5416", "#fdf5e6", "#dbc493"),
            "failed": ("#6e1c24", "#faeaeb", "#d99ea3"),
            "refunded": ("#5c534c", "#f0ece7", "#ccc4bd"),
        }
        color, bg, border = colors.get(obj.payment_status, ("#473831", "#f0ece7", "#ccc4bd"))
        return format_html(
            '<span style="background:{}; color:{}; border:1px solid {}; padding:2px 8px; border-radius:2px; font-weight:700; font-size:10px; font-family: Courier Prime, monospace; text-transform:uppercase;">{}</span>',
            bg, color, border, obj.get_payment_status_display()
        )

    payment_status_badge.short_description = "Payment"
    payment_status_badge.admin_order_field = "payment_status"

    def order_status_badge(self, obj):
        colors = {
            "delivered": ("#264e36", "#eaf2ed", "#9cbda9"),
            "shipped": ("#1e3a5f", "#e6edf5", "#a3b8cf"),
            "processing": ("#5b3a6e", "#f3ebf7", "#cbb3d6"),
            "confirmed": ("#1c535e", "#e7f3f5", "#a2cdd4"),
            "pending": ("#7a5416", "#fdf5e6", "#dbc493"),
            "cancelled": ("#6e1c24", "#faeaeb", "#d99ea3"),
        }
        color, bg, border = colors.get(obj.order_status, ("#473831", "#f0ece7", "#ccc4bd"))
        return format_html(
            '<span style="background:{}; color:{}; border:1px solid {}; padding:2px 8px; border-radius:2px; font-weight:700; font-size:10px; font-family: Courier Prime, monospace; text-transform:uppercase;">{}</span>',
            bg, color, border, obj.get_order_status_display()
        )

    order_status_badge.short_description = "Fulfillment"
    order_status_badge.admin_order_field = "order_status"

    @admin.action(description="Mark selected orders as Confirmed")
    def mark_confirmed(self, request, queryset):
        queryset.update(order_status="confirmed")

    @admin.action(description="Mark selected orders as Processing")
    def mark_processing(self, request, queryset):
        queryset.update(order_status="processing")

    @admin.action(description="Mark selected orders as Shipped")
    def mark_shipped(self, request, queryset):
        queryset.update(order_status="shipped")

    @admin.action(description="Mark selected orders as Delivered")
    def mark_delivered(self, request, queryset):
        queryset.update(order_status="delivered")

    @admin.action(description="Mark selected orders as Cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(order_status="cancelled")

    @admin.action(description="Mark selected orders as Paid")
    def mark_paid(self, request, queryset):
        queryset.update(payment_status="paid")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "unit_price", "subtotal"]
    search_fields = ["order__order_number", "product__name", "product__sku"]
    autocomplete_fields = ["order", "product"]
