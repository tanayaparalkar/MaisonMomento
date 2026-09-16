import os
import random
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.core.files import File

from apps.catalog.models import Category, Product, ProductImage
from apps.sales.models import Order, OrderItem
from apps.customers.models import Customer
from apps.recommendations.models import Interaction
from apps.tracking.models import VisitorSession


class Command(BaseCommand):
    help = "Seed rich development data for Maison Momento perfume retailer admin panel"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing Maison Momento development data seeding..."))

        # 1. Superuser
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@maisonmomento.com", "admin123")
            self.stdout.write(self.style.SUCCESS("[OK] Created superuser: admin / admin123"))
        else:
            self.stdout.write(self.style.WARNING("[*] Superuser 'admin' already exists."))

        # 2. Categories
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

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(cat_objs)} fragrance categories."))

        # 3. Create Media Product Images Helper
        media_products_dir = Path(settings.MEDIA_ROOT) / "products"
        os.makedirs(media_products_dir, exist_ok=True)

        def create_placeholder_image(product_name, cat_name, color_hex="#241610"):
            img_filename = f"{product_name.lower().replace(' ', '_')}.png"
            img_path = media_products_dir / img_filename
            
            # Always recreate with vintage styling
            img = Image.new("RGB", (400, 400), color="#1e150f")
            draw = ImageDraw.Draw(img)
            # Outer vintage brass border
            draw.rectangle([12, 12, 388, 388], outline="#b89047", width=2)
            # Inner fine hairline border
            draw.rectangle([18, 18, 382, 382], outline="#c9a45c", width=1)
            draw.rectangle([22, 22, 378, 378], outline="#473224", width=1)
            # Center apothecary cartouche
            draw.rectangle([45, 45, 355, 355], outline="#b89047", width=1)
            # Perfume flacon geometry
            draw.rectangle([175, 75, 225, 105], fill="#b89047")  # stopper
            draw.rectangle([130, 105, 270, 270], outline="#c9a45c", width=2)  # flacon
            draw.rectangle([140, 115, 260, 260], outline="#473224", width=1)  # inner facet
            # Vintage typography labels
            draw.text((200, 160), "MAISON", fill="#fbf8f2", anchor="mm")
            draw.text((200, 182), "MOMENTO", fill="#c9a45c", anchor="mm")
            draw.text((200, 215), cat_name.upper(), fill="#a89a8c", anchor="mm")
            draw.text((200, 310), "PARFUM EXTRAIT", fill="#b89047", anchor="mm")
            draw.text((200, 330), "FLACON DE VOYAGE", fill="#6b5f55", anchor="mm")
            img.save(img_path)
            
            return f"products/{img_filename}"

        # 4. Products (varied stock for inventory testing: >5, 1-5, 0)
        products_data = [
            # In Stock (> 5)
            {
                "name": "Santal Noir Extrait",
                "brand": "Maison Momento",
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
                "desc": "Rare Australian Mysore sandalwood layered with charred cedarwood, smoky birch tar, and rich ambergris."
            },
            {
                "name": "Royal Oud Imperial",
                "brand": "Maison Momento",
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
                "desc": "Aged 15-year Cambodian agarwood infused with dark saffron, leather accords, and Damascus rose petals."
            },
            {
                "name": "Bergamot Solstice",
                "brand": "Maison Momento",
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
                "desc": "Crisp sunny Calabrian bergamot, crushed petitgrain, sea salt accord, and sunlit vetiver."
            },
            {
                "name": "Néroli Riviera",
                "brand": "Maison Momento",
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
                "desc": "Tunisian orange blossoms, Italian mandarin, sea breeze notes, and sparkling white amber."
            },
            {
                "name": "Musc Impérial Précieux",
                "brand": "Maison Momento",
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
                "desc": "Velvety skin musks, powdery Tuscan Florentine orris root, ambrette seed, and cashmeran."
            },
            {
                "name": "Aqua di Positano",
                "brand": "Maison Momento",
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
                "desc": "Crisp mineral waves crashing over Amalfi coastal rocks, green sage, and sunny driftwood."
            },
            {
                "name": "Rose de Mai & Saffron",
                "brand": "Maison Momento",
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
                "desc": "Centifolia May rose from Grasse blended with precious Kashmiri red saffron threads and patchouli."
            },
            {
                "name": "Cuir d'Orient",
                "brand": "Maison Momento",
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
                "desc": "Polished saddlery leather, golden amber resin, burning cistus labdanum, and cardamom."
            },

            # Low Stock (1 – 5 units)
            {
                "name": "Fleur de Grasse",
                "brand": "Maison Momento",
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
                "desc": "Morning harvested jasmine sambac, French tuberose, and soft white musk."
            },
            {
                "name": "Vanilla Bourbon Velours",
                "brand": "Maison Momento",
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
                "desc": "Smoky dark Madagascar vanilla bean pods, brown rum, tonka bean, and cocoa butter."
            },
            {
                "name": "Cèdre Blanc & Vetiver",
                "brand": "Maison Momento",
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
                "desc": "Atlas cedarwood needles, Haitian vetiver roots, black pepper, and dry flint."
            },
            {
                "name": "Oud Sublime Royale",
                "brand": "Maison Momento",
                "sku": "MM-OUD-012",
                "cat": "Oud",
                "price": Decimal("34000.00"),
                "discount_price": None,
                "stock": 5,
                "gender": "unisex",
                "fragrance_family": "oud",
                "concentration": "parfum",
                "is_featured": True,
                "color": "#1c1917",
                "desc": "Rare wild Assamese oud wood resin, incense smoke, and royal saffron crystals."
            },

            # Out of Stock (0 units)
            {
                "name": "Ambre Nuit Enigmatique",
                "brand": "Maison Momento",
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
                "desc": "Nocturnal golden ambergris, frankincense, Turkish rose, and dark bourbon vanilla."
            },
            {
                "name": "Tabac Gourmand",
                "brand": "Maison Momento",
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
                "desc": "Cured blonde tobacco leaf, honeycomb, roasted cacao, and warm clove bark."
            },
            {
                "name": "Smoky Vetiver Accord",
                "brand": "Maison Momento",
                "sku": "MM-WOO-015",
                "cat": "Woody",
                "price": Decimal("16800.00"),
                "discount_price": None,
                "stock": 1,
                "gender": "men",
                "fragrance_family": "woody",
                "concentration": "edp",
                "is_featured": False,
                "color": "#111827",
                "desc": "Java vetiver root, roasted chestnuts, guaiac wood, and smoldering embers."
            },
            {
                "name": "Pure Cashmere Musc",
                "brand": "Maison Momento",
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
                "desc": "Clean white silk, warm cashmere woods, iris butter, and cozy cedar undertones."
            }
        ]

        product_objs = []
        for p_data in products_data:
            cat = cat_objs[p_data["cat"]]
            prod, created = Product.objects.get_or_create(
                sku=p_data["sku"],
                defaults={
                    "name": p_data["name"],
                    "brand": p_data["brand"],
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
            # Update price to INR if already existed
            prod.price = p_data["price"]
            prod.discount_price = p_data["discount_price"]
            prod.stock = p_data["stock"]
            prod.save(update_fields=["price", "discount_price", "stock"])

            # Create product image
            rel_img_path = create_placeholder_image(prod.name, cat.name, p_data["color"])
            if not prod.images.exists():
                ProductImage.objects.create(
                    product=prod,
                    image=rel_img_path,
                    alt_text=f"{prod.name} luxury flacon bottle",
                    is_primary=True,
                    display_order=0
                )
            product_objs.append(prod)

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(product_objs)} perfume products with local flacon images."))

        # 5. Customers (ready with sample Firebase UID)
        customers_data = [
            ("Victoria", "Sinclair", "victoria.sinclair@luxurylife.com", "+1-415-555-0192", "fb_uid_vic9201"),
            ("Alexander", "Sterling", "alex.sterling@mayfair.co.uk", "+44-20-7946-0921", "fb_uid_alex3842"),
            ("Camille", "Laurent", "camille.laurent@parisien.fr", "+33-1-42-68-55-11", "fb_uid_cam8472"),
            ("Julian", "Vance", "julian.vance@investor.com", "+1-212-555-0144", "fb_uid_julian911"),
            ("Elena", "Rostova", "elena.rostova@couture.it", "+39-02-555-4821", "fb_uid_elena774"),
            ("Marcus", "Chen", "marcus.chen@techventures.io", "+1-650-555-0187", "fb_uid_marcus28"),
            ("Sophia", "Al-Mansoor", "sophia.almansoor@gulfperfumes.ae", "+971-4-555-1928", "fb_uid_sophia93"),
            ("Sebastian", "Duval", "s.duval@genevaluxury.ch", "+41-22-555-8392", "fb_uid_seb1029"),
        ]

        cust_objs = []
        for fn, ln, email, phone, fb_uid in customers_data:
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
            cust_objs.append(cust)

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(cust_objs)} customer profiles with Firebase UID placeholders."))

        # 6. Orders and OrderItems across past 14 days
        now = timezone.now()
        statuses = [
            ("paid", "delivered"),
            ("paid", "shipped"),
            ("paid", "processing"),
            ("paid", "delivered"),
            ("paid", "confirmed"),
            ("pending", "pending"),
            ("paid", "delivered"),
            ("failed", "cancelled"),
        ]

        created_orders = []
        for i in range(16):
            days_ago = random.randint(0, 12)
            order_date = now - timedelta(days=days_ago, hours=random.randint(1, 18), minutes=random.randint(5, 50))
            cust = random.choice(cust_objs)
            pay_stat, ord_stat = random.choice(statuses)

            order = Order.objects.create(
                customer=cust,
                customer_name=cust.full_name,
                email=cust.email,
                phone=cust.phone,
                shipping_address=f"{random.randint(100, 999)} MG Road, Heritage Quarter, Suite {random.randint(10, 80)}",
                payment_status=pay_stat,
                order_status=ord_stat,
                shipping_cost=Decimal("250.00") if random.choice([True, False]) else Decimal("0.00"),
                discount=Decimal("1500.00") if random.choice([True, False]) else Decimal("0.00"),
            )
            # Backdate order
            Order.objects.filter(id=order.id).update(created_at=order_date)

            # Add 1 to 3 items
            chosen_prods = random.sample(product_objs[:10], k=random.randint(1, 3))
            subtotal = Decimal("0.00")
            for prod in chosen_prods:
                qty = random.choice([1, 1, 2])
                price = prod.effective_price
                item_sub = price * qty
                subtotal += item_sub
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    unit_price=price,
                    subtotal=item_sub
                )
            
            order.subtotal = subtotal
            order.total = max(Decimal("0.00"), subtotal - order.discount + order.shipping_cost)
            order.save(update_fields=["subtotal", "total"])
            created_orders.append(order)

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {len(created_orders)} historical orders with items."))

        # 7. Seed Interactions for Recommendation Engine & Analytics
        interactions_count = 0
        woody_prods = [p for p in product_objs if p.fragrance_family == "woody"]
        oud_prods = [p for p in product_objs if p.fragrance_family == "oud"]
        fresh_prods = [p for p in product_objs if p.fragrance_family == "fresh"]
        other_prods = [p for p in product_objs if p.fragrance_family not in ("woody", "oud", "fresh")]

        # Create stable VisitorSession objects for each seeded customer
        # These represent anonymous storefront sessions (no Django auth user attached)
        visitor_sessions = {}
        for cust in cust_objs:
            session_id = f"seed_visitor_{cust.id}"
            vs, _ = VisitorSession.objects.get_or_create(session_id=session_id)
            visitor_sessions[cust.id] = vs

        # Create a small pool of anonymous visitor sessions
        anon_sessions = []
        for i in range(5):
            vs, _ = VisitorSession.objects.get_or_create(session_id=f"seed_anon_{i}")
            anon_sessions.append(vs)

        # Seed focused interactions for Customer 0 (Victoria) heavily on Woody & Oud
        primary_cust = cust_objs[0]
        primary_visitor = visitor_sessions[primary_cust.id]
        for prod in woody_prods * 4:
            Interaction.objects.create(
                visitor=primary_visitor,
                product=prod,
                event_type="view",
            )
            interactions_count += 1

        for prod in oud_prods * 2:
            Interaction.objects.create(
                visitor=primary_visitor,
                product=prod,
                event_type="view",
            )
            interactions_count += 1

        # Seed interactions for other visitors / sessions
        for i in range(40):
            cust = random.choice(cust_objs + [None, None])
            prod = random.choice(product_objs)
            if cust:
                visitor = visitor_sessions[cust.id]
            else:
                visitor = random.choice(anon_sessions)
            itype = random.choice(["view", "view", "view"])
            inter = Interaction.objects.create(
                visitor=visitor,
                product=prod,
                event_type=itype,
            )
            # Randomize timestamps within past 10 days
            past_time = now - timedelta(days=random.randint(0, 8), hours=random.randint(0, 23))
            Interaction.objects.filter(id=inter.id).update(created_at=past_time)
            interactions_count += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {interactions_count} Interaction events for recommendation engine."))
        self.stdout.write(self.style.SUCCESS("*** Maison Momento development data seeding completed successfully!"))

