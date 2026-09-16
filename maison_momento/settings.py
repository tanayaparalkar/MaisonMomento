"""
Django settings for Maison Momento.

Environment variables are read from the process environment.
Copy .env.example to .env and fill in values for local development.
Never commit .env to version control.

Environment variable reference: see .env.example
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Lightweight .env loader
# Reads KEY=VALUE pairs from a .env file in the project root when it exists.
# This avoids requiring python-decouple while keeping local dev simple.
# Lines starting with # and blank lines are ignored.
# Values are NOT overridden if the variable is already set in the environment
# (so CI/CD environment variables always take precedence over .env).
# ---------------------------------------------------------------------------
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _value = _line.partition("=")
                os.environ.setdefault(_key.strip(), _value.strip())

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Authentication redirects
# ---------------------------------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:dashboard"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------------------
# Task 1 — SECRET KEY
# Reads from environment. Falls back to an insecure dev key ONLY when
# DEBUG=True so a missing env var is caught immediately in production.
# ---------------------------------------------------------------------------
_SECRET_KEY_FALLBACK = "django-insecure-local-dev-only-do-not-use-in-production"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _SECRET_KEY_FALLBACK)

# ---------------------------------------------------------------------------
# Task 2 — DEBUG
# Set DJANGO_DEBUG=False in production. Anything other than the string
# "True" (case-insensitive) is treated as False.
# ---------------------------------------------------------------------------
DEBUG = os.environ.get("DJANGO_DEBUG", "True").strip().lower() == "true"

# Fail loudly if the insecure fallback key is used outside of DEBUG mode.
if not DEBUG and SECRET_KEY == _SECRET_KEY_FALLBACK:
    raise RuntimeError(
        "DJANGO_SECRET_KEY environment variable must be set when DEBUG=False. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )

# ---------------------------------------------------------------------------
# Task 3 — ALLOWED_HOSTS
# Set DJANGO_ALLOWED_HOSTS as a comma-separated string in production.
# Example: DJANGO_ALLOWED_HOSTS=maisonmomento.com,www.maisonmomento.com
# Falls back to localhost/127.0.0.1 for local development when DEBUG=True.
# ---------------------------------------------------------------------------
_allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS", "")

if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    # Default Render support when running in production
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".onrender.com"]

_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com", "http://localhost:8000", "http://127.0.0.1:8000"]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Maison Momento domain apps
    "dashboard",
    "apps.catalog.apps.CatalogConfig",
    "apps.sales.apps.SalesConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.recommendations.apps.RecommendationsConfig",
    "apps.tracking.apps.TrackingConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tracking.middleware.VisitorTrackingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "maison_momento.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.unread_admin_notifications",
                "apps.customers.context_processors.wishlist_data",
                "apps.customers.context_processors.customer_notifications_data",
                "apps.sales.context_processors.cart_data",
            ],
        },
    },
]

WSGI_APPLICATION = "maison_momento.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# Supports DATABASE_URL (Render PostgreSQL) or local SQLite / PostgreSQL
# ---------------------------------------------------------------------------
import dj_database_url

_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    _db_engine = os.environ.get("DB_ENGINE", "sqlite3")
    if _db_engine in ("sqlite3", "django.db.backends.sqlite3"):
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": _db_engine if "." in _db_engine else f"django.db.backends.{_db_engine}",
                "NAME": os.environ.get("DB_NAME", "maison_momento"),
                "USER": os.environ.get("DB_USER", "tanaya"),
                "PASSWORD": os.environ.get("DB_PASSWORD", ""),
                "HOST": os.environ.get("DB_HOST", "localhost"),
                "PORT": os.environ.get("DB_PORT", "5432"),
            }
        }

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Task 5 — Static & Media files
# ---------------------------------------------------------------------------

# Static files
STATIC_URL = os.environ.get("STATIC_URL", "/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]     # Source files (not collected)
STATIC_ROOT = BASE_DIR / "staticfiles"        # Destination for collectstatic

# WhiteNoise compressed storage for production
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Media files (user-uploaded content)
MEDIA_URL = os.environ.get("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / "media"

# Extension point: future cloud storage backend
# DEFAULT_FILE_STORAGE = os.environ.get(
#     "DJANGO_DEFAULT_FILE_STORAGE",
#     "django.core.files.storage.FileSystemStorage",   # local fallback
# )
# STATICFILES_STORAGE = os.environ.get(
#     "DJANGO_STATICFILES_STORAGE",
#     "django.contrib.staticfiles.storage.StaticFilesStorage",  # local fallback
# )

# ---------------------------------------------------------------------------
# Retailer application configuration
# ---------------------------------------------------------------------------
LOW_STOCK_THRESHOLD = int(os.environ.get("LOW_STOCK_THRESHOLD", "5"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Task 4 — Security settings
# All security headers and cookie flags are automatically enabled when
# DEBUG=False. No manual toggling is required across environments.
# ---------------------------------------------------------------------------
# Tell Django it is behind a reverse proxy (Render / AWS / Cloudflare)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    # Force all traffic over HTTPS
    SECURE_SSL_REDIRECT = True

    # Protect session cookie from being sent over plain HTTP
    SESSION_COOKIE_SECURE = True

    # Protect CSRF cookie from being sent over plain HTTP
    CSRF_COOKIE_SECURE = True

    # Tell browsers to enforce HTTPS for 1 year (including subdomains)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Prevent the site being loaded inside an iframe (clickjacking protection)
    X_FRAME_OPTIONS = "DENY"

    # Opt out of MIME-type sniffing
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Redirect HTTP → HTTPS at the proxy layer for header-based detection
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    # Development: no HTTPS enforcement; iframes allowed for admin tooling
    X_FRAME_OPTIONS = "SAMEORIGIN"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        # Application loggers — INFO in development, WARNING in production
        "apps": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "dashboard": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        # Suppress noisy Django SQL in both environments
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Payment Gateway: Razorpay
# ---------------------------------------------------------------------------
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_CURRENCY = "INR"
PAYMENT_BACKEND = "apps.sales.services.providers.razorpay"


