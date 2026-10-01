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


class Occasion(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Occasion name (e.g. Office, Date Night, Wedding)")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Atmosphere and context for this occasion")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Occasion"
        verbose_name_plural = "Occasions"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FragranceNote(models.Model):
    """
    Individual olfactory note used across Top, Heart, and Base tiers of the pyramid.
    Normalized to support cross-perfume filtering, search, and future recommendation engines.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Olfactory note name (e.g. Bergamot, Rose, Oud)")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Scent profile and olfactory characteristics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fragrance Note"
        verbose_name_plural = "Fragrance Notes"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# Alias for developer convenience
Note = FragranceNote


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
    occasions = models.ManyToManyField(
        "catalog.Occasion",
        blank=True,
        related_name="products",
        help_text="Recommended occasions or settings for this fragrance"
    )
    top_notes = models.ManyToManyField(
        "catalog.FragranceNote",
        blank=True,
        related_name="top_note_products",
        help_text="Top / Opening notes (evaporate within 15–30 minutes)"
    )
    heart_notes = models.ManyToManyField(
        "catalog.FragranceNote",
        blank=True,
        related_name="heart_note_products",
        help_text="Heart / Middle notes forming the core character of the fragrance"
    )
    base_notes = models.ManyToManyField(
        "catalog.FragranceNote",
        blank=True,
        related_name="base_note_products",
        help_text="Base / Foundation notes that linger on the skin for hours"
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

    @property
    def average_rating(self):
        agg = self.reviews.filter(is_approved=True).aggregate(models.Avg("rating"))["rating__avg"]
        if agg is not None:
            return round(float(agg), 1)
        return 5.0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    def get_rating_distribution(self):
        total = self.review_count
        dist = []
        for star in range(5, 0, -1):
            count = self.reviews.filter(is_approved=True, rating=star).count()
            pct = round((count / total * 100), 1) if total > 0 else 0
            dist.append({
                "star": star,
                "count": count,
                "percentage": pct
            })
        return dist

    @property
    def has_fragrance_notes(self):
        """Return True if any olfactory tier has assigned notes."""
        return self.top_notes.exists() or self.heart_notes.exists() or self.base_notes.exists()

    @property
    def all_fragrance_notes(self):
        """Return all distinct fragrance notes in this perfume across all tiers."""
        return (self.top_notes.all() | self.heart_notes.all() | self.base_notes.all()).distinct()


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


class Review(models.Model):
    RATING_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="Product being reviewed"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        help_text="Associated customer account (optional)"
    )
    reviewer_name = models.CharField(max_length=150, help_text="Display name of reviewer")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, help_text="Rating between 1 and 5")
    title = models.CharField(max_length=255, blank=True, help_text="Optional review title")
    comment = models.TextField(help_text="Review content / olfactory impression")
    is_verified_purchase = models.BooleanField(default=False, help_text="Verified customer purchase status")
    is_approved = models.BooleanField(default=True, help_text="Designates whether review is approved and visible")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}★ Review for {self.product.name} by {self.reviewer_name}"

    @property
    def stars_display(self):
        return "★" * self.rating

    @property
    def empty_stars_display(self):
        return "☆" * (5 - self.rating)

