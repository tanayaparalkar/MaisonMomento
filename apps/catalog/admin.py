from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.conf import settings
from .models import Category, Product, ProductImage


class StockStatusFilter(admin.SimpleListFilter):
    title = "Inventory Status"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("in_stock", "In Stock (> 5)"),
            ("low_stock", "Low Stock (1 – 5)"),
            ("out_of_stock", "Out of Stock (0)"),
        )

    def queryset(self, request, queryset):
        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        if self.value() == "in_stock":
            return queryset.filter(stock__gt=threshold)
        elif self.value() == "low_stock":
            return queryset.filter(stock__gt=0, stock__lte=threshold)
        elif self.value() == "out_of_stock":
            return queryset.filter(stock=0)
        return queryset


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image_preview", "image", "alt_text", "is_primary", "display_order"]
    readonly_fields = ["image_preview"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 55px; height: 55px; object-fit: cover; border-radius: 6px; border: 1px solid #d4af37;" />',
                obj.image.url
            )
        return mark_safe('<span style="color: #888; font-size: 11px;">No Image</span>')

    image_preview.short_description = "Preview"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active_badge", "products_count_badge", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    actions = ["activate_categories", "deactivate_categories"]

    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success" style="background:#10b981; color:#fff; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">Active</span>')
        return mark_safe('<span class="badge badge-muted" style="background:#6b7280; color:#fff; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">Inactive</span>')

    is_active_badge.short_description = "Status"
    is_active_badge.admin_order_field = "is_active"

    def products_count_badge(self, obj):
        count = obj.products.count()
        return format_html('<span style="font-weight:600; color:#1e293b; background:#e2e8f0; padding:2px 8px; border-radius:10px;">{} items</span>', count)

    products_count_badge.short_description = "Products"

    @admin.action(description="Activate selected categories")
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} category/categories activated successfully.")

    @admin.action(description="Deactivate selected categories")
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} category/categories deactivated.")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "image_thumbnail",
        "name",
        "sku",
        "category",
        "formatted_price",
        "inventory_status_badge",
        "is_featured",
        "is_active",
        "updated_at",
    ]
    list_display_links = ["image_thumbnail", "name"]
    list_filter = [
        "category",
        "gender",
        "fragrance_family",
        "concentration",
        "is_featured",
        "is_active",
        StockStatusFilter,
    ]
    search_fields = ["name", "sku", "brand", "description"]
    ordering = ["-updated_at"]
    readonly_fields = ["created_at", "updated_at", "image_preview_large"]
    autocomplete_fields = ["category"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]

    fieldsets = (
        ("Core Information", {
            "fields": (("name", "slug"), ("brand", "sku"), "description", "category")
        }),
        ("Olfactory Profile", {
            "fields": (("fragrance_family", "concentration"), "gender")
        }),
        ("Pricing & Stock", {
            "fields": (("price", "discount_price"), "stock")
        }),
        ("Publishing & Showcase", {
            "fields": (("is_featured", "is_active"), "image_preview_large", ("created_at", "updated_at"))
        }),
    )

    actions = ["mark_featured", "unmark_featured", "mark_active", "mark_inactive"]

    def image_thumbnail(self, obj):
        primary = obj.primary_image
        if primary and primary.image:
            return format_html(
                '<img src="{}" style="width: 44px; height: 44px; object-fit: cover; border-radius: 8px; border: 1px solid #c5a880; box-shadow: 0 1px 3px rgba(0,0,0,0.12);" />',
                primary.image.url
            )
        return mark_safe(
            '<div style="width: 44px; height: 44px; border-radius: 8px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 10px; font-weight: 600;">No Pic</div>'
        )

    image_thumbnail.short_description = "Image"

    def image_preview_large(self, obj):
        primary = obj.primary_image
        if primary and primary.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; object-fit: cover; border-radius: 8px; border: 2px solid #c5a880;" />',
                primary.image.url
            )
        return "No image uploaded yet"

    image_preview_large.short_description = "Current Primary Image"

    def formatted_price(self, obj):
        if obj.discount_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #8c7e72; font-size: 11px; font-family: Courier Prime, monospace;">₹{}</span> <strong style="color: #6e1c24; font-weight:700; font-family: Courier Prime, monospace;">₹{}</strong>',
                f"{obj.price:,.2f}",
                f"{obj.discount_price:,.2f}"
            )
        return format_html('<strong style="font-family: Courier Prime, monospace;">₹{}</strong>', f"{obj.price:,.2f}")

    formatted_price.short_description = "Price (₹)"
    formatted_price.admin_order_field = "price"

    def inventory_status_badge(self, obj):
        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        if obj.stock > threshold:
            return format_html(
                '<span class="badge badge-in-stock">[IN STOCK: {}]</span>',
                obj.stock
            )
        elif obj.stock > 0:
            return format_html(
                '<span class="badge badge-low-stock">[LOW STOCK: {}]</span>',
                obj.stock
            )
        return mark_safe(
            '<span class="badge badge-out-of-stock">[OUT OF STOCK]</span>'
        )

    inventory_status_badge.short_description = "Stock"
    inventory_status_badge.admin_order_field = "stock"

    @admin.action(description="Mark selected as Featured")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Remove selected from Featured")
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description="Activate selected products")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected products")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["thumbnail", "product", "is_primary", "display_order", "alt_text", "created_at"]
    list_filter = ["is_primary", "created_at"]
    search_fields = ["product__name", "product__sku", "alt_text"]
    autocomplete_fields = ["product"]

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px; border: 1px solid #ccc;" />',
                obj.image.url
            )
        return "No Image"

    thumbnail.short_description = "Image"
