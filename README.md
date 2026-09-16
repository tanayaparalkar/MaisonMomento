# Maison Momento — Vintage Parfumeur & Apothécaire Platform

A vintage, old-school retailer-focused platform and operations center engineered for **Maison Momento** (Haute Parfumerie, Attar & Fine Fragrances).

---

## 🏛️ Vintage Apothecary Features

### 1. Currency in Indian Rupees (₹)
- All catalog formulations, discounts, invoices, line items, and analytics metrics are denominated in **Indian Rupees (₹)** (e.g. ₹12,500.00 – ₹34,000.00).
- Chart.js timeline tracks `REVENUE (INR ₹)` with formatted ticks.

### 2. Dignified, Emoji-Free Interface
- **Zero emojis** across all navigation headers, executive cards, data tables, filter menus, and inventory badges.
- Classic archival tags: `[IN STOCK: 18]`, `[LOW STOCK: 3]`, `[OUT OF STOCK]`.

### 3. Vintage Heritage Typography & Colors
- **Serif Typography**: *Cormorant Garamond*, *Cinzel*, and *Libre Baskerville* paired with *Courier Prime* for SKU codes and financial figures.
- **Palette**: Aged leather (`#241610`), warm brass (`#b89047`), antique gold (`#c9a45c`), and archival parchment paper (`#f6f2ea`).
- **Flacon Images**: Bottle placeholders generated with brass cartouche frames and vintage French perfumery typography.

### 4. Catalog & Olfactory Profile Management
- 8 Fragrance Families: *Woody, Oud, Fresh, Floral, Citrus, Gourmand, Oriental, Musky*.
- Concentrations: *Parfum / Extrait, Eau de Parfum, Eau de Toilette, Eau de Cologne, Eau Fraîche*.
- Inline image gallery, display ordering, and primary showcase designation.

### 5. Sales & Order Register
- Sequential order numbering (`MM-YYYYMMDD-XXXX`), customer addresses, subtotal, shipping, discount, and total in rupees.
- Fulfillment statuses: *Pending, Confirmed, Processing, Shipped, Delivered, Cancelled*.

### 6. Client CRM & Lifetime Value
- Full names, email, telephone number, and indexed `firebase_uid` field ready for future Firebase Authentication.
- Real-time aggregated order counts, total paid spend in rupees, and last order dates.

### 7. Category-Based Recommendation Service
- Modular recency-weighted category scoring in `apps/recommendations/services.py` (`get_recommendations`).
- Prioritizes top-affinity categories and filters out out-of-stock items.

---

## 🚀 Quickstart: Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations (Local SQLite only)
python manage.py migrate

# 3. Seed development data (INR prices & vintage flacon images)
python manage.py seed_dev_data

# 4. Start development server
python manage.py runserver
```

**Credentials & Access**:
- **Storefront**: [http://127.0.0.1:8000/products/](http://127.0.0.1:8000/products/)
- **Staff Dashboard**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- **Username**: `admin`
- **Password**: `admin123`