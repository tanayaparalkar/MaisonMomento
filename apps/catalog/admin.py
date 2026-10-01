from django.contrib import admin
from .models import Category, FragranceNote, Occasion, Product, ProductImage, Review


@admin.register(FragranceNote)
class FragranceNoteAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "top_count", "heart_count", "base_count", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    def top_count(self, obj):
        return obj.top_note_products.count()
    top_count.short_description = "Top Tier"

    def heart_count(self, obj):
        return obj.heart_note_products.count()
    heart_count.short_description = "Heart Tier"

    def base_count(self, obj):
        return obj.base_note_products.count()
    base_count.short_description = "Base Tier"


@admin.register(Occasion)
class OccasionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active", "product_count")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("display_order", "is_active")

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Perfumes"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "reviewer_name", "rating", "is_approved", "is_verified_purchase", "created_at")
    list_filter = ("rating", "is_approved", "is_verified_purchase", "created_at")
    search_fields = ("reviewer_name", "title", "comment", "product__name")
    actions = ["approve_reviews", "reject_reviews"]
    list_editable = ["is_approved"]

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    reject_reviews.short_description = "Reject selected reviews"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active", "is_featured")
    list_filter = ("is_active", "is_featured", "category", "fragrance_family", "occasions")
    search_fields = ("name", "sku", "description")
    filter_horizontal = ("occasions", "top_notes", "heart_notes", "base_notes")
    inlines = [ProductImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

