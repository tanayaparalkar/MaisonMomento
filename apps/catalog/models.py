from django.db import models
from django.utils.text import slugify
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Category name (e.g. Woody, Oud, Floral)")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Olfactory profile and category description")
    is_active = models.BooleanField(default=True, help_text="Designates whether this category is active in catalog")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def product_count(self):
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    GENDER_CHOICES = [
        ("unisex", "Unisex"),
        ("men", "Men"),
        ("women", "Women"),
    ]

    FRAGRANCE_FAMILY_CHOICES = [
        ("woody", "Woody"),
        ("oud", "Oud"),
        ("fresh", "Fresh"),
        ("floral", "Floral"),
        ("citrus", "Citrus"),
        ("gourmand", "Gourmand"),
        ("oriental", "Oriental"),
        ("musky", "Musky"),
    ]

    CONCENTRATION_CHOICES = [
        ("parfum", "Parfum / Extrait de Parfum"),
        ("edp", "Eau de Parfum (EDP)"),
        ("edt", "Eau de Toilette (EDT)"),
        ("edc", "Eau de Cologne (EDC)"),
        ("eau_fraiche", "Eau Fraîche"),
    ]

    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    brand = models.CharField(max_length=150, default="Maison Momènto", db_index=True)
    sku = models.CharField(max_length=64, unique=True, help_text="Unique Stock Keeping Unit")
    description = models.TextField(help_text="Detailed scent notes, accord composition, and description")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Retail price in INR (₹)")
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Promotional discount price (optional)"
    )
    stock = models.PositiveIntegerField(default=0, help_text="Current available inventory quantity")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products",
        help_text="Primary fragrance classification"
    )
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default="unisex")
    fragrance_family = models.CharField(
        max_length=50,
        choices=FRAGRANCE_FAMILY_CHOICES,
        default="woody",
        help_text="Olfactory fragrance family"
    )
    concentration = models.CharField(
        max_length=50,
        choices=CONCENTRATION_CHOICES,
        default="edp",
        help_text="Perfume oil concentration"
    )
    is_featured = models.BooleanField(default=False, help_text="Display prominently on featured showcase")
    is_active = models.BooleanField(default=True, help_text="Product visibility status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.brand} - {self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand}-{self.name}")
        super().save(*args, **kwargs)

    @property
    def inventory_status(self):
        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        if self.stock > threshold:
            return "in_stock"
        elif self.stock > 0:
            return "low_stock"
        return "out_of_stock"

    @property
    def inventory_status_label(self):
        status = self.inventory_status
        if status == "in_stock":
            return "In Stock"
        elif status == "low_stock":
            return "Low Stock"
        return "Out of Stock"

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        if not primary:
            primary = self.images.order_by("display_order", "id").first()
        return primary

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False, help_text="Designate this image as the main showcase image")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which image appears")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"Image for {self.product.name} ({'Primary' if self.is_primary else f'#{self.display_order}'})"

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Deselect any other primary image for this product
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
