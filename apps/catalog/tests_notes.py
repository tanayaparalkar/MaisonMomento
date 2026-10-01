"""
apps/catalog/tests_notes.py
===========================
Automated test suite for the Fragrance Notes (Olfactory Pyramid) system.
Tests:
- FragranceNote model creation and slugification.
- Product relationship to Top, Heart, and Base notes.
- Product properties: has_fragrance_notes and all_fragrance_notes.
- Cross-perfume and cross-tier note sharing for future recommendation engines.
- Product detail view rendering the Olfactory Pyramid.
- Staff dashboard ProductForm saving fragrance notes.
"""

from decimal import Decimal
from django.db.models import Q
from django.test import TestCase, Client
from django.urls import reverse

from apps.catalog.models import Category, FragranceNote, Product
from dashboard.forms import ProductForm


class FragranceNoteModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Woody", slug="woody")
        self.bergamot = FragranceNote.objects.create(name="Calabrian Bergamot")
        self.rose = FragranceNote.objects.create(name="Damascus Rose")
        self.oud = FragranceNote.objects.create(name="Cambodian Agarwood")
        self.saffron = FragranceNote.objects.create(name="Dark Saffron")

    def test_note_creation_and_slug(self):
        self.assertEqual(str(self.bergamot), "Calabrian Bergamot")
        self.assertEqual(self.bergamot.slug, "calabrian-bergamot")

    def test_product_pyramid_assignment(self):
        product = Product.objects.create(
            name="Imperial Oud",
            sku="SKU-IMPERIAL-OUD",
            price=Decimal("12000.00"),
            category=self.category,
        )
        self.assertFalse(product.has_fragrance_notes)

        product.top_notes.add(self.bergamot, self.saffron)
        product.heart_notes.add(self.rose)
        product.base_notes.add(self.oud)

        self.assertTrue(product.has_fragrance_notes)
        self.assertEqual(product.top_notes.count(), 2)
        self.assertEqual(product.heart_notes.count(), 1)
        self.assertEqual(product.base_notes.count(), 1)
        self.assertEqual(product.all_fragrance_notes.count(), 4)

    def test_shared_note_across_tiers_and_perfumes(self):
        """
        Verify that a single normalized note can be a Top note in one perfume
        and a Heart note in another, supporting future recommendation engine filters.
        """
        perfume_a = Product.objects.create(
            name="Scent Alpha",
            sku="SKU-ALPHA",
            price=Decimal("8000.00"),
            category=self.category,
        )
        perfume_b = Product.objects.create(
            name="Scent Beta",
            sku="SKU-BETA",
            price=Decimal("9500.00"),
            category=self.category,
        )

        # Bergamot as top in A, and as heart in B
        perfume_a.top_notes.add(self.bergamot)
        perfume_b.heart_notes.add(self.bergamot)

        # Reverse query
        self.assertIn(perfume_a, self.bergamot.top_note_products.all())
        self.assertIn(perfume_b, self.bergamot.heart_note_products.all())

        # Recommendation engine shared-note query
        matching_products = Product.objects.filter(
            Q(top_notes=self.bergamot) |
            Q(heart_notes=self.bergamot) |
            Q(base_notes=self.bergamot)
        ).distinct()
        self.assertEqual(matching_products.count(), 2)
        self.assertIn(perfume_a, matching_products)
        self.assertIn(perfume_b, matching_products)


class ProductDetailPyramidViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Oud", slug="oud")
        self.product = Product.objects.create(
            name="Royal Assamese",
            sku="SKU-ROYAL-ASSAM",
            price=Decimal("15000.00"),
            category=self.category,
            is_active=True,
        )
        self.top_note = FragranceNote.objects.create(name="Pink Pepper")
        self.heart_note = FragranceNote.objects.create(name="French Lavender")
        self.base_note = FragranceNote.objects.create(name="Assamese Wild Oud")

        self.product.top_notes.add(self.top_note)
        self.product.heart_notes.add(self.heart_note)
        self.product.base_notes.add(self.base_note)

    def test_olfactory_pyramid_rendered_on_pdp(self):
        response = self.client.get(reverse("catalog:product_detail", kwargs={"pk": self.product.pk}))
        self.assertEqual(response.status_code, 200)

        # Section header
        self.assertContains(response, "Olfactory Pyramid")
        self.assertContains(response, "The Harmonic Composition")

        # Three column tier headers
        self.assertContains(response, "Top Notes")
        self.assertContains(response, "Heart Notes")
        self.assertContains(response, "Base Notes")

        # Specific notes
        self.assertContains(response, "Pink Pepper")
        self.assertContains(response, "French Lavender")
        self.assertContains(response, "Assamese Wild Oud")


class DashboardProductNotesFormTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Citrus", slug="citrus")
        self.note1 = FragranceNote.objects.create(name="Sicilian Lemon")
        self.note2 = FragranceNote.objects.create(name="Tunisian Neroli")
        self.note3 = FragranceNote.objects.create(name="Haitian Vetiver")

    def test_product_form_saves_notes(self):
        form_data = {
            "name": "Soleil de Capri",
            "brand": "Maison Momènto",
            "sku": "SKU-SOLEIL-CAPRI",
            "category": self.category.id,
            "gender": "unisex",
            "fragrance_family": "citrus",
            "concentration": "edp",
            "price": "7500.00",
            "description": "Sun-drenched citrus and vetiver.",
            "top_notes": [self.note1.id],
            "heart_notes": [self.note2.id],
            "base_notes": [self.note3.id],
            "is_active": True,
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()

        self.assertEqual(product.top_notes.count(), 1)
        self.assertEqual(product.heart_notes.count(), 1)
        self.assertEqual(product.base_notes.count(), 1)
        self.assertIn(self.note1, product.top_notes.all())
        self.assertIn(self.note2, product.heart_notes.all())
        self.assertIn(self.note3, product.base_notes.all())
