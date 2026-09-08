from django.contrib import admin
from django.db.models import Count, Sum, Max, Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "full_name_display",
        "email",
        "phone",
        "date_joined",
        "order_count_badge",
        "formatted_total_spent",
        "last_order_date_display",
    ]
    list_display_links = ["full_name_display", "email"]
    search_fields = ["first_name", "last_name", "email", "phone", "firebase_uid"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "firebase_uid", "total_spent_display", "orders_summary"]

    fieldsets = (
        ("Personal Information", {
            "fields": (("first_name", "last_name"), ("email", "phone"), "is_active")
        }),
        ("Authentication & Integration", {
            "fields": ("firebase_uid", ("created_at", "updated_at"))
        }),
        ("Lifetime Value Metrics", {
            "fields": ("total_spent_display", "orders_summary")
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            annotated_order_count=Count("orders", distinct=True),
            annotated_total_spent=Sum(
                "orders__total",
                filter=Q(orders__payment_status="paid"),
                default=0.00
            ),
            annotated_last_order=Max("orders__created_at")
        )

    def full_name_display(self, obj):
        return format_html(
            '<strong style="color: #0f172a;">{} {}</strong>',
            obj.first_name,
            obj.last_name
        )

    full_name_display.short_description = "Name"
    full_name_display.admin_order_field = "first_name"

    def date_joined(self, obj):
        return obj.created_at.strftime("%b %d, %Y")

    date_joined.short_description = "Date Joined"
    date_joined.admin_order_field = "created_at"

    def order_count_badge(self, obj):
        count = getattr(obj, "annotated_order_count", obj.number_of_orders)
        return format_html(
            '<span style="background: #eee7d8; color: #3d261a; border: 1px solid #dcd3c1; padding: 2px 8px; border-radius: 2px; font-weight: 700; font-size: 10px; font-family: Courier Prime, monospace;">{} ORDERS</span>',
            count
        )

    order_count_badge.short_description = "Orders"
    order_count_badge.admin_order_field = "annotated_order_count"

    def formatted_total_spent(self, obj):
        amount = getattr(obj, "annotated_total_spent", obj.total_spent) or 0.00
        return format_html(
            '<span style="font-weight: 700; color: #264e36; font-family: Courier Prime, monospace;">₹{}</span>',
            f"{amount:,.2f}"
        )

    formatted_total_spent.short_description = "Total Spent (₹)"
    formatted_total_spent.admin_order_field = "annotated_total_spent"

    def last_order_date_display(self, obj):
        date = getattr(obj, "annotated_last_order", None)
        if not date and obj.last_order:
            date = obj.last_order.created_at
        if date:
            return date.strftime("%b %d, %Y %H:%M")
        return mark_safe('<span style="color: #8c7e72; font-style: italic;">No orders yet</span>')

    last_order_date_display.short_description = "Last Order"
    last_order_date_display.admin_order_field = "annotated_last_order"

    def total_spent_display(self, obj):
        return f"₹{obj.total_spent:,.2f}"

    total_spent_display.short_description = "Total Paid Spent (₹)"

    def orders_summary(self, obj):
        orders = obj.orders.all()[:5]
        if not orders:
            return "No orders placed by this customer."
        html = '<ul style="margin: 0; padding-left: 20px; font-family: Libre Baskerville, Georgia, serif;">'
        for order in orders:
            html += f'<li><strong>#{order.order_number}</strong> &mdash; ₹{order.total:,.2f} ({order.get_order_status_display()}, {order.get_payment_status_display()}) &mdash; {order.created_at.strftime("%b %d, %Y")}</li>'
        html += '</ul>'
        return mark_safe(html)

    orders_summary.short_description = "Recent Orders"
