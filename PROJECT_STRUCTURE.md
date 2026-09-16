# 1. Project Overview

Maison Momento is a Django-based premium fragrance e-commerce platform. It provides a luxurious online storefront for customers to browse and purchase high-end fragrances, while offering a comprehensive administrative backend for staff. 

Key features include:
- **Customer Storefront**: Premium catalogue, shopping cart, and checkout flow.
- **Staff Dashboard**: Operational center for managing the business.
- **Recommendation Engine**: Provides related product suggestions.
- **Inventory Management**: Tracks stock and historical adjustments.
- **Order Management**: Processes lifecycle states of customer orders.
- **Notification System**: Internal event-driven alerts for staff and customers.
- **CSV Export**: Data export capabilities for reporting.
- **SQLite / PostgreSQL**: Relational database storage.

---

# 2. High-Level Architecture

The platform follows a classic Django Model-View-Template (MVT) architecture augmented with a strict Service Layer to encapsulate business logic. 

**Request Flow:**
Browser → URLs → Views → Service Layer → Domain Apps (Models) → Database

**Separation of Concerns:**
- **Storefront**: Driven by domain apps (`apps/catalog`, `apps/sales`, `apps/customers`) which serve customer-facing views and templates.
- **Dashboard**: A dedicated operational module (`dashboard/`) that provides authenticated staff access to manage the domain apps. It has its own views, URL routing, styles, and templates, completely isolated from the customer storefront.

---

# 3. Folder Structure

```
MaisonMomento/
├── apps/
│   ├── catalog/
│   ├── customers/
│   ├── inventory/
│   ├── notifications/
│   ├── recommendations/
│   ├── sales/
│   └── tracking/
├── dashboard/
│   ├── static/
│   └── templates/
├── docs/
├── maison_momento/
├── media/
├── static/
├── templates/
├── manage.py
├── requirements.txt
└── README.md
```

---

# 4. Apps

### apps/catalog
- **Purpose**: Responsible for the product catalogue, categories, browsing, filtering, and product detail pages.
- **Contains**: `models.py`, `views.py` (directory), `urls.py`, `management/`

### apps/customers
- **Purpose**: Handles customer profiles, wishlists, and user authentication mapping.
- **Contains**: `models.py`, `views.py`, `urls.py`, `services.py`

### apps/inventory
- **Purpose**: Dedicated domain for tracking product stock levels and adjustment histories.
- **Contains**: `models.py`, `views.py`, `services.py`, `tests.py`

### apps/notifications
- **Purpose**: Event-driven internal notification infrastructure.
- **Contains**: `models.py`, `services.py`, `tests.py`, `events.py`

### apps/recommendations
- **Purpose**: Generates and serves product recommendations based on algorithms/rules.
- **Contains**: `models.py`, `services/` (directory)

### apps/sales
- **Purpose**: Manages shopping carts, checkout, order processing, and payment status.
- **Contains**: `models.py`, `views.py`, `urls.py`, `services/` (directory), `tests.py`

### apps/tracking
- **Purpose**: Tracks visitor sessions and product interactions for analytics.
- **Contains**: `models.py`, `views.py`, `tests.py`

---

# 5. Dashboard

The `dashboard/` module acts as a monolithic admin application overlaying the domain services. It provides the UI and views for all operational tasks.

**Major Features**:
- **Product Management**: Create, edit, and archive fragrances.
- **Inventory**: Monitor stock, low-stock warnings, and log stock adjustments.
- **Orders**: View order details and transition workflow states (e.g. Pending -> Shipped).
- **Clients**: View customer profiles and purchase history.
- **Recommendations**: Monitor engine health and trending algorithms.
- **Insights**: View aggregated sales analytics and charts.
- **Exports**: Download CSV reports for business data.
- **Notifications**: View system alerts and operational issues.
- **Settings**: Administrative configuration.

**Locations**:
- **Templates**: `dashboard/templates/dashboard/`
- **CSS/JS**: `dashboard/static/dashboard/` (contains `css/`, `js/`, `images/`)

---

# 6. Templates

**Major Template Groups**:
- `templates/catalog/`: Storefront catalogue, product lists, and detail pages.
- `templates/sales/`: Storefront cart and checkout flows.
- `templates/customers/`: Customer account pages and notifications.
- `templates/registration/`: Branded login and authentication views.
- `templates/admin/`: Overridden Django admin templates (e.g., custom admin login, category management).
- `dashboard/templates/dashboard/`: Operational dashboard interface.

---

# 7. Static Files

**Frontend Assets (Storefront)**:
Stored in `static/`
- **CSS**: `static/css/` (e.g., `storefront.css`, `login.css`)
- **Fonts, Images, Icons**: Handled externally (e.g. Unsplash, Google Fonts) or within media.

**Frontend Assets (Dashboard)**:
Stored in `dashboard/static/dashboard/`
- **CSS**: `dashboard/static/dashboard/css/` (e.g., `dashboard.css`)
- **JS**: `dashboard/static/dashboard/js/` 
- **Images**: `dashboard/static/dashboard/images/`

---

# 8. Documentation

- `docs/`: Contains extension notes (e.g., `notifications_extension_points.md`).
- *Note: Architecture diagrams, ER diagrams, and workflow diagrams were generated as system artifacts during previous AI sessions rather than committed directly to the repository.*

---

# 9. Testing

Tests are organized alongside their respective apps to ensure domain encapsulation.
The project currently passes **76 tests** across the suite.
- **Tested Apps**: `apps/inventory`, `apps/notifications`, `apps/sales`, `apps/tracking`, `dashboard/`

---

# 10. UI Areas

### Storefront
- Home
- Collections
- Catalogue (Fragrances)
- Product Detail
- Wishlist
- Cart
- Checkout
- Notifications (Customer)
- Account (Profile)
- Login

### Staff Dashboard
- Dashboard (Overview)
- Products (Catalogue Management)
- Inventory
- Orders
- Clients
- Recommendations (Health & Tuning)
- Exports
- Notifications (System & Operational)
- Settings

---

# 11. Important Files

**Storefront & Shared**:
- `templates/catalog/base.html` (Main Storefront Layout & Navigation)
- `static/css/storefront.css` (Main Storefront Styling & Theme)
- `templates/catalog/includes/product_card.html` (Reusable Product Card)
- `templates/registration/login.html` (Unified Login Layout)

**Dashboard**:
- `dashboard/templates/dashboard/base.html` (Main Dashboard Layout & Navigation)
- `dashboard/static/dashboard/css/dashboard.css` (Main Dashboard Styling & Theme)

---

# 12. Frontend Dependency Map

- **Navigation**: `templates/catalog/base.html`, `dashboard/templates/dashboard/base.html`
- **Dashboard**: `dashboard/templates/dashboard/dashboard.html`, `dashboard.css`
- **Storefront**: `templates/catalog/base.html`, `storefront.css`
- **Cards**: `templates/catalog/includes/product_card.html`, `storefront.css`
- **Buttons**: `storefront.css`, `dashboard.css`
- **Search**: `templates/catalog/base.html`, `templates/catalog/product_list.html`
- **Animations**: Defined within `storefront.css` and `dashboard.css`
- **Typography & Theme**: CSS custom properties in `dashboard.css` (inherited by storefront)
- **Notifications**: `dashboard/templates/dashboard/notifications.html`, `templates/customers/notifications.html`, `base.html` (for badges)
- **Wishlist**: `templates/catalog/base.html` (JS logic and badge), `product_detail.html`
- **Cart Badge**: `templates/catalog/base.html` (JS update function and DOM element)
- **Header/Footer**: Defined entirely within `templates/catalog/base.html` (Storefront) and `dashboard/templates/dashboard/base.html` (Admin)

---

# 13. File Request Guide

### Recommended Files for UI Polish

If you are beginning a frontend UI/UX polish pass, request these foundational files first to understand the layout, structure, and design system constraints:

**Storefront Foundations**:
1. `templates/catalog/base.html`
2. `static/css/storefront.css`

**Dashboard Foundations**:
3. `dashboard/templates/dashboard/base.html`
4. `dashboard/static/dashboard/css/dashboard.css`

**Key Reusable Components**:
5. `templates/catalog/includes/product_card.html`
6. `templates/registration/login.html`

*Request these files to analyze the current styling tokens (colors, typography, grid systems) before modifying specific views like the Cart, Checkout, or individual Dashboard pages.*
