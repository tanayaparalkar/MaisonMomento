import os
import random
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from PIL import Image, ImageDraw

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone

from apps.catalog.models import Category, Product, ProductImage
from apps.sales.models import Order, OrderItem, Cart, CartItem
from apps.customers.models import Customer, Wishlist
from apps.inventory.models import StockAdjustment
from apps.notifications.models import Notification
from apps.recommendations.models import Interaction
from apps.tracking.models import VisitorSession


class Command(BaseCommand):
    help = "Seed rich, authentic development data for Maison Momènto luxury fragrance platform."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("================================================================"))
        self.stdout.write(self.style.NOTICE(" Initializing Maison Momento Complete Data Seeding Engine..."))
        self.stdout.write(self.style.NOTICE("================================================================"))

        now = timezone.now()
        User = get_user_model()

        # ---------------------------------------------------------------------
        # 1. Staff & Superuser Accounts
        # ---------------------------------------------------------------------
        if not User.objects.filter(username="admin").exists():
            admin_user = User.objects.create_superuser("admin", "admin@maisonmomento.com", "admin123")
            admin_user.first_name = "Directeur"
            admin_user.last_name = "Général"
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("[OK] Created Superuser: admin / admin123"))
        else:
            admin_user = User.objects.get(username="admin")
            self.stdout.write(self.style.WARNING("[*] Superuser 'admin' already exists."))

        concierge_user, _ = User.objects.get_or_create(
            username="concierge",
            defaults={
                "email": "concierge@maisonmomento.com",
                "first_name": "Maison",
                "last_name": "Concierge",
                "is_staff": True,
            }
        )
        concierge_user.set_password("concierge123")
        concierge_user.is_staff = True
        concierge_user.save()

        # ---------------------------------------------------------------------
        # 2. Olfactory Fragrance Families (Categories)
        # ---------------------------------------------------------------------
        categories_data = [
            ("Woody", "Earthy cedar, sandalwood, patchouli, vetiver and smoky resinous accords.", "woody"),
            ("Oud", "Precious agarwood, dark amber, leather, and Middle Eastern regal aromatics.", "oud"),
            ("Fresh", "Crisp aquatic ocean breeze, morning dew, green tea, and invigorating aromatics.", "fresh"),
            ("Floral", "Damask rose, jasmine sambac, iris pallida, tuberose, and royal garden essences.", "floral"),
            ("Citrus", "Sparkling Calabrian bergamot, blood orange, Amalfi lemon, and crisp neroli.", "citrus"),
            ("Gourmand", "Warm Madagascar vanilla, tonka bean, roasted coffee, hazelnut, and praline.", "gourmand"),
            ("Oriental", "Sensual amber, spicy saffron, benzoin, incense, and golden oriental resins.", "oriental"),
            ("Musky", "Soft velvet cashmere, white musk, clean linen, and enveloping skin scents.", "musky"),
        ]

        cat_objs = {}
        for name, desc, code in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={"description": desc, "is_active": True}
            )
            cat_objs[name] = cat

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(cat_objs)} Olfactory Fragrance Families."))

        # ---------------------------------------------------------------------
        # 3. Flacon Images Helper
        # ---------------------------------------------------------------------
        media_products_dir = Path(settings.MEDIA_ROOT) / "products"
        os.makedirs(media_products_dir, exist_ok=True)

        def get_or_create_flacon_image(product_name, cat_name, color_hex="#241610"):
            filename_map = {
                "Santal Noir Extrait": "santal_noir_extrait.png",
                "Royal Oud Imperial": "royal_oud_imperial.png",
                "Bergamot Solstice": "bergamont_solistice.png",
                "Néroli Riviera": "neroli_riviera.png",
                "Musc Impérial Précieux": "music_imperial_precieux.png",
                "Aqua di Positano": "aqua_di_positano.png",
                "Rose de Mai & Saffron": "rose_de_mai_&_saffron.png",
                "Cuir d'Orient": "cuir_d_orient.png",
                "Fleur de Grasse": "fleur_de_grasse.png",
                "Vanilla Bourbon Velours": "vanilla_bourbon_velours.png",
                "Cèdre Blanc & Vetiver": "cedre_blanc_&_vetiver.png",
                "Oud Sublime Royale": "oud_sublime_royal.png",
                "Ambre Nuit Enigmatique": "ambre_nuit_enigmatique.png",
                "Tabac Gourmand": "tabac_gourmand.png",
                "Smoky Vetiver Accord": "smoky_vetiver_accord.png",
                "Pure Cashmere Musc": "pure_cashmere_music.png",
            }

            img_filename = filename_map.get(product_name, f"{product_name.lower().replace(' ', '_')}.png")
            img_path = media_products_dir / img_filename

            # If photo exists, keep it
            if img_path.exists():
                return f"products/{img_filename}"

            # Otherwise generate luxury vintage graphic with MOMÈNTO
            img = Image.new("RGB", (400, 400), color="#1e150f")
            draw = ImageDraw.Draw(img)
            draw.rectangle([12, 12, 388, 388], outline="#b89047", width=2)
            draw.rectangle([18, 18, 382, 382], outline="#c9a45c", width=1)
            draw.rectangle([22, 22, 378, 378], outline="#473224", width=1)
            draw.rectangle([45, 45, 355, 355], outline="#b89047", width=1)
            draw.rectangle([175, 75, 225, 105], fill="#b89047")
            draw.rectangle([130, 105, 270, 270], outline="#c9a45c", width=2)
            draw.rectangle([140, 115, 260, 260], outline="#473224", width=1)
            draw.text((200, 160), "MAISON", fill="#fbf8f2", anchor="mm")
            draw.text((200, 182), "MOMÈNTO", fill="#c9a45c", anchor="mm")
            draw.text((200, 215), cat_name.upper(), fill="#a89a8c", anchor="mm")
            draw.text((200, 310), "PARFUM EXTRAIT", fill="#b89047", anchor="mm")
            draw.text((200, 330), "FLACON DE VOYAGE", fill="#6b5f55", anchor="mm")
            img.save(img_path)

            return f"products/{img_filename}"

        # ---------------------------------------------------------------------
        # 4. Products Catalog (16 Luxury Fragrances)
        # ---------------------------------------------------------------------
        products_data = [
            # In Stock (> 5)
            {
                "name": "Santal Noir Extrait",
                "brand": "Maison Momènto",
                "sku": "MM-SAN-001",
                "cat": "Woody",
                "price": Decimal("24500.00"),
                "discount_price": Decimal("21500.00"),
                "stock": 18,
                "gender": "unisex",
                "fragrance_family": "woody",
                "concentration": "parfum",
                "is_featured": True,
                "color": "#1c1917",
                "desc": "Rare Australian Mysore sandalwood layered with charred cedarwood, smoky birch tar, and rich golden ambergris. Top Notes: Cardamom, Bergamot. Heart Notes: Papyrus, Orris, Mysore Sandalwood. Base Notes: Cedarwood, Ambergris, Leather. Concentration: 36% Extrait de Parfum."
            },
            {
                "name": "Royal Oud Imperial",
                "brand": "Maison Momènto",
                "sku": "MM-OUD-002",
                "cat": "Oud",
                "price": Decimal("29000.00"),
                "discount_price": None,
                "stock": 12,
                "gender": "unisex",
                "fragrance_family": "oud",
                "concentration": "parfum",
                "is_featured": True,
                "color": "#291b16",
                "desc": "Aged 15-year Cambodian agarwood infused with dark saffron, leather accords, and Damascus rose petals. Top Notes: Saffron, Pink Pepper. Heart Notes: Taif Rose, Geranium, Oud Wood. Base Notes: Smoked Leather, Labdanum, Benzoin. Concentration: 32% Extrait de Parfum."
            },
            {
                "name": "Bergamot Solstice",
                "brand": "Maison Momènto",
                "sku": "MM-CIT-003",
                "cat": "Citrus",
                "price": Decimal("12500.00"),
                "discount_price": None,
                "stock": 25,
                "gender": "unisex",
                "fragrance_family": "citrus",
                "concentration": "edt",
                "is_featured": False,
                "color": "#1e293b",
                "desc": "Crisp sunny Calabrian bergamot, crushed petitgrain, sea salt accord, and sunlit vetiver. Top Notes: Calabrian Bergamot, Lemon Zest. Heart Notes: Neroli, Petitgrain, Sea Salt. Base Notes: Vetiver, White Musk, Driftwood. Concentration: Eau de Toilette."
            },
            {
                "name": "Néroli Riviera",
                "brand": "Maison Momènto",
                "sku": "MM-FRE-004",
                "cat": "Fresh",
                "price": Decimal("14000.00"),
                "discount_price": None,
                "stock": 19,
                "gender": "unisex",
                "fragrance_family": "fresh",
                "concentration": "edp",
                "is_featured": False,
                "color": "#0f172a",
                "desc": "Tunisian orange blossoms, Italian mandarin, sea breeze notes, and sparkling white amber. Top Notes: Mandarine, Neroli. Heart Notes: Orange Blossom, Lavender, Aquatic Notes. Base Notes: Amber, Angelica, Cedar. Concentration: Eau de Parfum."
            },
            {
                "name": "Musc Impérial Précieux",
                "brand": "Maison Momènto",
                "sku": "MM-MUS-005",
                "cat": "Musky",
                "price": Decimal("18500.00"),
                "discount_price": None,
                "stock": 14,
                "gender": "unisex",
                "fragrance_family": "musky",
                "concentration": "edp",
                "is_featured": True,
                "color": "#18181b",
                "desc": "Velvety skin musks, powdery Tuscan Florentine orris root, ambrette seed, and cashmeran. Top Notes: Ambrette Seed, White Pepper. Heart Notes: Orris Butter, Heliotrope. Base Notes: Tonkin Musk Accord, Cashmeran, Sandalwood. Concentration: Eau de Parfum."
            },
            {
                "name": "Aqua di Positano",
                "brand": "Maison Momènto",
                "sku": "MM-FRE-006",
                "cat": "Fresh",
                "price": Decimal("13500.00"),
                "discount_price": None,
                "stock": 22,
                "gender": "men",
                "fragrance_family": "fresh",
                "concentration": "edt",
                "is_featured": False,
                "color": "#082f49",
                "desc": "Crisp mineral waves crashing over Amalfi coastal rocks, green sage, and sunny driftwood. Top Notes: Marine Accord, Italian Lemon. Heart Notes: Clary Sage, Rosemary, Geranium. Base Notes: Driftwood, Oakmoss, Ambergris. Concentration: Eau de Toilette."
            },
            {
                "name": "Rose de Mai & Saffron",
                "brand": "Maison Momènto",
                "sku": "MM-FLO-007",
                "cat": "Floral",
                "price": Decimal("22000.00"),
                "discount_price": None,
                "stock": 10,
                "gender": "women",
                "fragrance_family": "floral",
                "concentration": "edp",
                "is_featured": True,
                "color": "#3f1d2e",
                "desc": "Centifolia May rose from Grasse blended with precious Kashmiri red saffron threads and patchouli. Top Notes: Kashmiri Saffron, Blackcurrant. Heart Notes: Grasse Rose de Mai, Turkish Rose. Base Notes: Indonesian Patchouli, Vanilla, Oud. Concentration: Eau de Parfum."
            },
            {
                "name": "Cuir d'Orient",
                "brand": "Maison Momènto",
                "sku": "MM-ORI-008",
                "cat": "Oriental",
                "price": Decimal("23500.00"),
                "discount_price": None,
                "stock": 8,
                "gender": "unisex",
                "fragrance_family": "oriental",
                "concentration": "parfum",
                "is_featured": False,
                "color": "#27170a",
                "desc": "Polished saddlery leather, golden amber resin, burning cistus labdanum, and cardamom. Top Notes: Green Cardamom, Thyme. Heart Notes: Tuscan Leather, Violet, Suede. Base Notes: Golden Amber, Incense, Birch Tar. Concentration: 28% Extrait de Parfum."
            },

            # Low Stock (1 – 5 units)
            {
                "name": "Fleur de Grasse",
                "brand": "Maison Momènto",
                "sku": "MM-FLO-009",
                "cat": "Floral",
                "price": Decimal("16500.00"),
                "discount_price": Decimal("14800.00"),
                "stock": 3,
                "gender": "women",
                "fragrance_family": "floral",
                "concentration": "edp",
                "is_featured": False,
                "color": "#3b0764",
                "desc": "Morning harvested jasmine sambac, French tuberose, and soft white musk. Top Notes: Bergamot, Orange Blossom. Heart Notes: Jasmine Sambac, Indian Tuberose. Base Notes: White Musk, Bourbon Vanilla, Sandalwood. Concentration: Eau de Parfum."
            },
            {
                "name": "Vanilla Bourbon Velours",
                "brand": "Maison Momènto",
                "sku": "MM-GOU-010",
                "cat": "Gourmand",
                "price": Decimal("15500.00"),
                "discount_price": None,
                "stock": 2,
                "gender": "unisex",
                "fragrance_family": "gourmand",
                "concentration": "edp",
                "is_featured": False,
                "color": "#451a03",
                "desc": "Smoky dark Madagascar vanilla bean pods, brown rum, tonka bean, and cocoa butter. Top Notes: Aged Rum, Roasted Almond. Heart Notes: Madagascar Vanilla Pods, Dark Cocoa. Base Notes: Tonka Bean, Benzoin, Cedarwood. Concentration: Eau de Parfum."
            },
            {
                "name": "Cèdre Blanc & Vetiver",
                "brand": "Maison Momènto",
                "sku": "MM-WOO-011",
                "cat": "Woody",
                "price": Decimal("17500.00"),
                "discount_price": None,
                "stock": 4,
                "gender": "men",
                "fragrance_family": "woody",
                "concentration": "edp",
                "is_featured": False,
                "color": "#14532d",
                "desc": "Atlas cedarwood needles, Haitian vetiver roots, black pepper, and dry flint. Top Notes: Black Pepper, Elemi, Grapefruit. Heart Notes: Atlas Cedar, Haitian Vetiver. Base Notes: Patchouli, Oakmoss, Benzoin. Concentration: Eau de Parfum."
            },
            {
                "name": "Oud Sublime Royale",
                "brand": "Maison Momènto",
                "sku": "MM-OUD-012",
                "cat": "Oud",
                "price": Decimal("34000.00"),
                "discount_price": None,
                "stock": 3,
                "gender": "unisex",
                "fragrance_family": "oud",
                "concentration": "parfum",
                "is_featured": True,
                "color": "#1c1917",
                "desc": "Rare wild Assamese oud wood resin, incense smoke, and royal saffron crystals. Top Notes: Nutmeg, Saffron, Incense. Heart Notes: Assam Agarwood, Smoked Birch. Base Notes: Amber, Castoreum, Myrrh. Concentration: 38% Extrait de Parfum."
            },

            # Out of Stock (0 units)
            {
                "name": "Ambre Nuit Enigmatique",
                "brand": "Maison Momènto",
                "sku": "MM-ORI-013",
                "cat": "Oriental",
                "price": Decimal("26000.00"),
                "discount_price": None,
                "stock": 0,
                "gender": "unisex",
                "fragrance_family": "oriental",
                "concentration": "parfum",
                "is_featured": False,
                "color": "#312e81",
                "desc": "Nocturnal golden ambergris, frankincense, Turkish rose, and dark bourbon vanilla. Top Notes: Pink Pepper, Bergamot. Heart Notes: Turkish Rose, Ambergris. Base Notes: Frankincense, Cistus, Vanilla. Concentration: 30% Extrait de Parfum."
            },
            {
                "name": "Tabac Gourmand",
                "brand": "Maison Momènto",
                "sku": "MM-GOU-014",
                "cat": "Gourmand",
                "price": Decimal("24000.00"),
                "discount_price": None,
                "stock": 0,
                "gender": "unisex",
                "fragrance_family": "gourmand",
                "concentration": "parfum",
                "is_featured": False,
                "color": "#3f1c07",
                "desc": "Cured blonde tobacco leaf, honeycomb, roasted cacao, and warm clove bark. Top Notes: Tobacco Leaf, Spicy Notes. Heart Notes: Tonka Bean, Tobacco Blossom, Cacao. Base Notes: Dried Fruit Accord, Woody Notes. Concentration: Extrait de Parfum."
            },
            {
                "name": "Smoky Vetiver Accord",
                "brand": "Maison Momènto",
                "sku": "MM-WOO-015",
                "cat": "Woody",
                "price": Decimal("16800.00"),
                "discount_price": None,
                "stock": 0,
                "gender": "men",
                "fragrance_family": "woody",
                "concentration": "edp",
                "is_featured": False,
                "color": "#111827",
                "desc": "Java vetiver root, roasted chestnuts, guaiac wood, and smoldering embers. Top Notes: Roasted Chestnut, Orange Blossom. Heart Notes: Java Vetiver, Guaiac Wood. Base Notes: Clove Oil, Smoldering Birch, Cashmere Wood. Concentration: Eau de Parfum."
            },
            {
                "name": "Pure Cashmere Musc",
                "brand": "Maison Momènto",
                "sku": "MM-MUS-016",
                "cat": "Musky",
                "price": Decimal("19500.00"),
                "discount_price": None,
                "stock": 11,
                "gender": "unisex",
                "fragrance_family": "musky",
                "concentration": "edp",
                "is_featured": False,
                "color": "#262626",
                "desc": "Clean white silk, warm cashmere woods, iris butter, and cozy cedar undertones. Top Notes: Aldehydes, White Silk Accord. Heart Notes: Tuscan Iris Butter, Cashmeran. Base Notes: White Musk, Iso E Super, Amber. Concentration: Eau de Parfum."
            }
        ]

        product_objs = []
        for p_data in products_data:
            cat = cat_objs[p_data["cat"]]
            prod, _ = Product.objects.get_or_create(
                sku=p_data["sku"],
                defaults={
                    "name": p_data["name"],
                    "brand": "Maison Momènto",
                    "description": p_data["desc"],
                    "price": p_data["price"],
                    "discount_price": p_data["discount_price"],
                    "stock": p_data["stock"],
                    "category": cat,
                    "gender": p_data["gender"],
                    "fragrance_family": p_data["fragrance_family"],
                    "concentration": p_data["concentration"],
                    "is_featured": p_data["is_featured"],
                    "is_active": True,
                }
            )
            # Ensure name, brand, description, and price are in sync
            prod.name = p_data["name"]
            prod.brand = "Maison Momènto"
            prod.description = p_data["desc"]
            prod.price = p_data["price"]
            prod.discount_price = p_data["discount_price"]
            prod.stock = p_data["stock"]
            prod.category = cat
            prod.gender = p_data["gender"]
            prod.fragrance_family = p_data["fragrance_family"]
            prod.concentration = p_data["concentration"]
            prod.is_featured = p_data["is_featured"]
            prod.is_active = True
            prod.save()

            # Product image
            rel_img_path = get_or_create_flacon_image(prod.name, cat.name, p_data["color"])
            if not prod.images.exists():
                ProductImage.objects.create(
                    product=prod,
                    image=rel_img_path,
                    alt_text=f"{prod.name} - Maison Momènto Luxury Flacon",
                    is_primary=True,
                    display_order=0
                )
            else:
                img_obj = prod.images.first()
                img_obj.image = rel_img_path
                img_obj.alt_text = f"{prod.name} - Maison Momènto Luxury Flacon"
                img_obj.save()

            product_objs.append(prod)

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(product_objs)} Luxury Perfumes under 'Maison Momènto'."))

        # ---------------------------------------------------------------------
        # 5. Customers & Matching Django Auth Users
        # ---------------------------------------------------------------------
        customers_data = [
            ("Victoria", "Sinclair", "victoria.sinclair@luxurylife.com", "+1-415-555-0192", "fb_uid_vic9201", "Penthouse 14B, The Imperial Towers, Tardeo, Mumbai, Maharashtra 400034"),
            ("Alexander", "Sterling", "alex.sterling@mayfair.co.uk", "+44-20-7946-0921", "fb_uid_alex3842", "18 Grosvenor Square, Mayfair, London W1K 6JP, United Kingdom"),
            ("Camille", "Laurent", "camille.laurent@parisien.fr", "+33-1-42-68-55-11", "fb_uid_cam8472", "24 Place Vendôme, 75001 Paris, France"),
            ("Priya", "Sharma", "priya.sharma@archstudio.in", "+91-98200-11234", "fb_uid_priya92", "Flat 8A, Sea Face Park, Bhulabhai Desai Road, Mumbai, Maharashtra 400026"),
            ("Arjun", "Mehra", "arjun.mehra@heritagegallery.in", "+91-98110-88765", "fb_uid_arjun44", "74 Jor Bagh, New Delhi, Delhi 110003"),
            ("Julian", "Vance", "julian.vance@investor.com", "+1-212-555-0144", "fb_uid_julian911", "740 Park Avenue, Apt 11A, New York, NY 10021, USA"),
            ("Elena", "Rostova", "elena.rostova@couture.it", "+39-02-555-4821", "fb_uid_elena774", "Via Montenapoleone 8, 20121 Milano MI, Italy"),
            ("Marcus", "Chen", "marcus.chen@techventures.io", "+1-650-555-0187", "fb_uid_marcus28", "Ardmore Park #16-02, Singapore 259958"),
            ("Sophia", "Al-Mansoor", "sophia.almansoor@gulfperfumes.ae", "+971-4-555-1928", "fb_uid_sophia93", "Villa 42, Palm Jumeirah, Dubai, United Arab Emirates"),
            ("Sebastian", "Duval", "s.duval@genevaluxury.ch", "+41-22-555-8392", "fb_uid_seb1029", "Rue du Rhône 40, 1204 Genève, Switzerland"),
            ("Ananya", "Singhania", "ananya.singhania@textiles.in", "+91-98300-44567", "fb_uid_ananya12", "14 Queens Park, Ballygunge, Kolkata, West Bengal 700019"),
            ("Rohan", "Kirloskar", "rohan.k@automotivedesign.in", "+91-98500-99881", "fb_uid_rohan67", "Bungalow 7, North Main Road, Koregaon Park, Pune, Maharashtra 411001"),
        ]

        cust_objs = []
        for fn, ln, email, phone, fb_uid, addr in customers_data:
            cust, _ = Customer.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "phone": phone,
                    "firebase_uid": fb_uid,
                    "is_active": True,
                }
            )
            cust.first_name = fn
            cust.last_name = ln
            cust.phone = phone
            cust.is_active = True
            cust.save()
            cust._shipping_address = addr
            cust_objs.append(cust)

            # Create matching Django User so customer portal authentication works seamlessly
            username = email.split("@")[0].replace(".", "_")
            u, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": fn, "last_name": ln}
            )
            u.first_name = fn
            u.last_name = ln
            u.email = email
            u.set_password("customer123")
            u.save()

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(cust_objs)} VIP Customers and User accounts (password: customer123)."))

        # ---------------------------------------------------------------------
        # 6. Customer Wishlists
        # ---------------------------------------------------------------------
        Wishlist.objects.all().delete()
        wishlist_count = 0
        for cust in cust_objs:
            # 2 to 4 favorite scents per customer
            chosen = random.sample(product_objs, k=random.randint(2, 4))
            for p in chosen:
                Wishlist.objects.get_or_create(customer=cust, product=p)
                wishlist_count += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {wishlist_count} Wishlist items across customers."))

        # ---------------------------------------------------------------------
        # 7. Active Shopping Carts
        # ---------------------------------------------------------------------
        CartItem.objects.all().delete()
        Cart.objects.all().delete()
        for cust in cust_objs[:4]:
            cart, _ = Cart.objects.get_or_create(customer=cust)
            chosen_sample = random.sample(product_objs[:8], k=random.randint(1, 2))
            for p in chosen_sample:
                CartItem.objects.create(cart=cart, product=p, quantity=random.choice([1, 1, 2]))

        self.stdout.write(self.style.SUCCESS("[OK] Seeded active Shopping Carts for customer sessions."))

        # ---------------------------------------------------------------------
        # 8. Realistic Orders & Line Items (Past 45 Days up to TODAY)
        # ---------------------------------------------------------------------
        OrderItem.objects.all().delete()
        Order.objects.all().delete()

        created_orders = []

        # (A) Orders TODAY (to guarantee today's revenue, shipments, deliveries, pending, confirmed)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_scenarios = [
            # customer_idx, pay_status, order_status
            (0, "paid", "delivered"),   # Victoria - delivered via boutique courier
            (1, "paid", "delivered"),   # Alexander - delivered
            (3, "paid", "shipped"),     # Priya - shipped with tracking
            (5, "paid", "shipped"),     # Julian - shipped
            (4, "paid", "confirmed"),   # Arjun - confirmed & awaiting packing
            (6, "pending", "pending"),  # Elena - pending payment confirmation
            (8, "pending", "pending"),  # Sophia - pending confirmation
        ]

        total_seconds_today = max(600, int((now - today_start).total_seconds()))
        for idx, (c_idx, p_stat, o_stat) in enumerate(today_scenarios):
            c = cust_objs[c_idx]
            sec_offset = int((total_seconds_today * (idx + 1)) / (len(today_scenarios) + 1))
            o_date = today_start + timedelta(seconds=max(60, sec_offset))
            date_code = o_date.strftime("%Y%m%d")
            order_num = f"MM-{date_code}-{uuid.uuid4().hex[:6].upper()}"

            order = Order.objects.create(
                order_number=order_num,
                customer=c,
                customer_name=c.full_name,
                email=c.email,
                phone=c.phone,
                shipping_address=getattr(c, "_shipping_address", "The Imperial Towers, Mumbai"),
                payment_status=p_stat,
                order_status=o_stat,
                notes="Fragrance gift packaging with emerald wax seal and personalized card.",
                razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
                razorpay_payment_id=f"pay_{uuid.uuid4().hex[:14]}" if p_stat == "paid" else None,
                shipping_cost=Decimal("0.00"),
                discount=Decimal("2000.00") if p_stat == "paid" else Decimal("0.00"),
            )
            Order.objects.filter(id=order.id).update(created_at=o_date, updated_at=o_date)

            # Items
            items_to_add = random.sample(product_objs[:8], k=random.randint(1, 2))
            subtotal = Decimal("0.00")
            for prod in items_to_add:
                qty = 1
                price = prod.effective_price
                subtotal += price * qty
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    unit_price=price,
                    subtotal=price * qty
                )
            order.subtotal = subtotal
            order.total = max(Decimal("0.00"), subtotal - order.discount + order.shipping_cost)
            order.save(update_fields=["subtotal", "total"])
            created_orders.append(order)

        # (B) Orders Across Past 1 to 180 Days (Spanning last 6 months for complete insights)
        historical_days = [
            1, 1, 2, 2, 3, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 18, 20, 22, 24, 25, 28,
            32, 35, 38, 42, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110, 120, 130, 140, 150, 165, 175
        ]
        historical_scenarios = []
        for days_ago in historical_days:
            if days_ago == 15:
                p_stat, o_stat = "refunded", "refunded"
            elif days_ago == 25:
                p_stat, o_stat = "failed", "cancelled"
            else:
                p_stat = "paid"
                o_stat = "shipped" if days_ago <= 3 else "delivered"
            historical_scenarios.append((days_ago, p_stat, o_stat))

        for days_ago, p_stat, o_stat in historical_scenarios:
            c = random.choice(cust_objs)
            o_date = now - timedelta(days=days_ago, hours=random.randint(1, 22), minutes=random.randint(0, 59))
            date_code = o_date.strftime("%Y%m%d")
            order_num = f"MM-{date_code}-{uuid.uuid4().hex[:6].upper()}"

            has_disc = random.choice([True, False, False])
            disc_amount = Decimal("1500.00") if has_disc else Decimal("0.00")
            ship_cost = Decimal("0.00") if random.choice([True, True, False]) else Decimal("250.00")

            order = Order.objects.create(
                order_number=order_num,
                customer=c,
                customer_name=c.full_name,
                email=c.email,
                phone=c.phone,
                shipping_address=getattr(c, "_shipping_address", "Heritage Quarter, Mumbai"),
                payment_status=p_stat,
                order_status=o_stat,
                notes="Client preferred courier dispatch with tracking alerts." if p_stat == "paid" else "",
                razorpay_order_id=f"order_{uuid.uuid4().hex[:14]}",
                razorpay_payment_id=f"pay_{uuid.uuid4().hex[:14]}" if p_stat == "paid" else None,
                shipping_cost=ship_cost,
                discount=disc_amount,
            )
            Order.objects.filter(id=order.id).update(created_at=o_date, updated_at=o_date)

            chosen_prods = random.sample(product_objs, k=random.randint(1, 3))
            subtotal = Decimal("0.00")
            for prod in chosen_prods:
                qty = random.choice([1, 1, 1, 2])
                price = prod.effective_price
                subtotal += price * qty
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    unit_price=price,
                    subtotal=price * qty
                )
            order.subtotal = subtotal
            order.total = max(Decimal("0.00"), subtotal - order.discount + order.shipping_cost)
            order.save(update_fields=["subtotal", "total"])
            created_orders.append(order)

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(created_orders)} authentic Orders with line items & financial totals."))

        # ---------------------------------------------------------------------
        # 9. Inventory History (Stock Adjustments)
        # ---------------------------------------------------------------------
        StockAdjustment.objects.all().delete()
        adj_records = [
            ("Santal Noir Extrait", 25, 5, 30, "restock", "Compounding consignment MM-GR-2026-09 arrived from Grasse laboratory.", 28),
            ("Royal Oud Imperial", 15, 4, 19, "restock", "Restocked 15 flacons of aged Cambodian agarwood reserve.", 22),
            ("Bergamot Solstice", 30, 8, 38, "restock", "Calabrian harvest distillation batch replenishment.", 18),
            ("Cèdre Blanc & Vetiver", -1, 5, 4, "damaged", "1 flacon damaged during customs unpacking inspection.", 14),
            ("Rose de Mai & Saffron", -2, 12, 10, "manual_correction", "Allocated 2 display flacons for Flagship Boutique olfactory bar.", 10),
            ("Oud Sublime Royale", 5, 1, 6, "restock", "Special reserve small-batch delivery received from Grasse atelier.", 7),
            ("Fleur de Grasse", 10, 2, 12, "restock", "Restock of May harvesting jasmine formulation.", 5),
            ("Vanilla Bourbon Velours", -1, 3, 2, "decrease", "Reserved for VIP collector private tasting concierge.", 3),
            ("Ambre Nuit Enigmatique", -4, 4, 0, "decrease", "Depleted through high-demand private orders. Scheduled for autumn batch.", 2),
            ("Smoky Vetiver Accord", 10, 1, 11, "restock", "New batch compounded and cleared by quality assurance.", 1),
        ]

        for p_name, delta, prev_s, new_s, adj_type, reason, days_ago in adj_records:
            prod_match = next((p for p in product_objs if p.name == p_name), None)
            if prod_match:
                adj = StockAdjustment.objects.create(
                    product=prod_match,
                    quantity=delta,
                    previous_stock=prev_s,
                    new_stock=new_s,
                    adjustment_type=adj_type,
                    reason=reason,
                    admin_user=admin_user,
                )
                adj_date = now - timedelta(days=days_ago, hours=random.randint(1, 12))
                StockAdjustment.objects.filter(id=adj.id).update(created_at=adj_date)

        self.stdout.write(self.style.SUCCESS("[OK] Seeded authentic Stock Adjustment audit history."))

        # ---------------------------------------------------------------------
        # 10. Staff & Customer Notifications
        # ---------------------------------------------------------------------
        Notification.objects.all().delete()
        admin_notifications = [
            ("inventory_critical", "admin", "warning", "Low Stock Alert: Vanilla Bourbon Velours", "Only 2 units remain in central climate-controlled warehouse.", "/dashboard/inventory/"),
            ("inventory_out_of_stock", "admin", "error", "Out of Stock: Ambre Nuit Enigmatique", "Inventory depleted. Awaiting scheduled Grasse autumn compounding.", "/dashboard/inventory/"),
            ("vip_order", "admin", "success", "VIP Order Received: ₹53,000", "Victoria Sinclair placed order #MM-2026-TODAY. Requested green wax seal wrapping.", "/dashboard/orders/"),
            ("customs_cleared", "admin", "info", "Consignment Inbound: Grasse Atelier", "50 flacons cleared Mumbai customs air freight cargo and transferred to depot.", "/dashboard/inventory/"),
            ("client_registration", "admin", "info", "New Concierge Client: Sophia Al-Mansoor", "Client from Dubai registered with interest in Oud & Amber accords.", "/dashboard/clients/"),
        ]

        for n_type, target, sev, title, msg, url in admin_notifications:
            Notification.objects.create(
                notification_type=n_type,
                target_type=target,
                severity=sev,
                title=title,
                message=msg,
                url=url,
                recipient=admin_user,
                is_read=False,
            )

        # Customer Notifications
        vic_user = User.objects.filter(email="victoria.sinclair@luxurylife.com").first()
        if vic_user:
            Notification.objects.create(
                notification_type="order_shipped",
                target_type="customer",
                severity="info",
                title="Your Maison Momènto Order Has Been Dispatched",
                message="Your Santal Noir Extrait is en route with express white-glove courier.",
                url="/cart/orders/",
                recipient=vic_user,
                is_read=False,
            )
            Notification.objects.create(
                notification_type="welcome",
                target_type="customer",
                severity="success",
                title="Bienvenue to Maison Momènto",
                message="Your personal fragrance concierge is at your service for bespoke appointments.",
                url="/about/",
                recipient=vic_user,
                is_read=True,
            )

        priya_user = User.objects.filter(email="priya.sharma@archstudio.in").first()
        if priya_user:
            Notification.objects.create(
                notification_type="order_update",
                target_type="customer",
                severity="success",
                title="Order #MM-2026-0917 Confirmed",
                message="Your order is being compounded and hand-boxed in our bespoke packaging.",
                url="/cart/orders/",
                recipient=priya_user,
                is_read=False,
            )

        self.stdout.write(self.style.SUCCESS("[OK] Seeded Staff & Customer Notification dispatch queues."))

        # ---------------------------------------------------------------------
        # 11. Visitor Sessions & Recommendation Engine Interactions
        # ---------------------------------------------------------------------
        Interaction.objects.all().delete()
        VisitorSession.objects.all().delete()

        # Seed authenticated sessions
        visitor_sessions = []
        for cust in cust_objs:
            username = cust.email.split("@")[0].replace(".", "_")
            user_inst = User.objects.filter(username=username).first()
            vs = VisitorSession.objects.create(
                session_id=f"sess_{cust.id}_{uuid.uuid4().hex[:8]}",
                user=user_inst,
                is_active=True
            )
            visitor_sessions.append(vs)

        # Seed anonymous visitor sessions
        for i in range(15):
            vs = VisitorSession.objects.create(
                session_id=f"anon_sess_{i}_{uuid.uuid4().hex[:8]}",
                user=None,
                is_active=True
            )
            visitor_sessions.append(vs)

        # Seed 220 realistic interactions with strong fragrance correlations
        interactions_seeded = 0
        event_types = ["view", "view", "view", "search", "wishlist", "cart", "purchase", "recommendation_click"]

        for vs in visitor_sessions:
            # Pick a preferred scent category per visitor for genuine collaborative filtering
            fav_family = random.choice(["woody", "oud", "fresh", "floral", "oriental", "gourmand"])
            affinity_prods = [p for p in product_objs if p.fragrance_family == fav_family]
            if not affinity_prods:
                affinity_prods = product_objs[:4]

            # 4 to 8 interactions per session
            for _ in range(random.randint(4, 8)):
                p = random.choice(affinity_prods if random.random() < 0.75 else product_objs)
                ev = random.choice(event_types)
                inter = Interaction.objects.create(
                    visitor=vs,
                    product=p,
                    event_type=ev,
                    metadata={"referrer": "/collections/", "device": random.choice(["mobile", "desktop"])}
                )
                past_time = now - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23), minutes=random.randint(0, 59))
                Interaction.objects.filter(id=inter.id).update(created_at=past_time)
                interactions_seeded += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(visitor_sessions)} Visitor Sessions & {interactions_seeded} Olfactory Interactions."))

        self.stdout.write(self.style.NOTICE("================================================================"))
        self.stdout.write(self.style.SUCCESS(" *** Maison Momento Luxury Store & Ops Center Seeded Successfully! ***"))
        self.stdout.write(self.style.NOTICE("================================================================"))
