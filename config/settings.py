"""
Settings for the Nomad Explorer Tours website.

Everything secret or environment specific is read from environment variables
(see .env.example). Without DATABASE_URL the site falls back to SQLite and
without Supabase S3 keys uploads go to the local "media/" folder, so the
project runs locally with zero setup.
"""
import os
from pathlib import Path

import dj_database_url
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

# Load a local .env file if present (simple KEY=VALUE lines, no dependency needed).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return str(env(name, str(default))).lower() in ("1", "true", "yes", "on")


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY") or ("dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Set SECRET_KEY in the environment variables.")

ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

RENDER_HOST = env("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "tours",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tours.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: Supabase Postgres via DATABASE_URL (use the "Session pooler" string, port 5432).
DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=int(env("DB_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
            ssl_require=env_bool("DB_SSL_REQUIRE", True),
        )
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# Page-data cache shared by all gunicorn workers on the server (see tours/cache.py).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env("CACHE_DIR", "/tmp/nomad-tours-cache"),
        "TIMEOUT": 60 * 30,
        "OPTIONS": {"MAX_ENTRIES": 3000},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Images: Supabase Storage through its S3 protocol. The bucket must be Public.
SUPABASE_URL = env("SUPABASE_URL", "").rstrip("/")
SUPABASE_BUCKET = env("SUPABASE_BUCKET", "nomad")
if env("SUPABASE_S3_ACCESS_KEY_ID"):
    _default_storage = {
        "BACKEND": "tours.storage.SupabaseStorage",
        "OPTIONS": {
            "bucket_name": SUPABASE_BUCKET,
            "endpoint_url": f"{SUPABASE_URL}/storage/v1/s3",
            "access_key": env("SUPABASE_S3_ACCESS_KEY_ID"),
            "secret_key": env("SUPABASE_S3_SECRET_ACCESS_KEY"),
            "region_name": env("SUPABASE_S3_REGION", "eu-central-1"),
            "addressing_style": "path",
            "signature_version": "s3v4",
            "file_overwrite": False,
            "querystring_auth": False,
            # Every upload gets a unique name, so browsers may cache images for a year.
            "object_parameters": {"CacheControl": "public, max-age=31536000, immutable"},
        },
    }
else:
    _default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": _default_storage,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# Public address of the site, e.g. https://www.nomadexplorertours.com (used for SEO links).
SITE_URL = env("SITE_URL", f"https://{RENDER_HOST}" if RENDER_HOST else "http://localhost:8000").rstrip("/")

# Email notifications for new enquiries (optional). Without EMAIL_HOST nothing is sent;
# enquiries are still saved and shown in the dashboard.
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@localhost")
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_TIMEOUT = 15
ENQUIRY_NOTIFY_EMAIL = env("ENQUIRY_NOTIFY_EMAIL", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # tours with long itineraries have many inline fields

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"tours": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")}},
}

# ---------------------------------------------------------------------------
# Admin dashboard (django-unfold)
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Nomad Explorer Admin",
    "SITE_HEADER": "Nomad Explorer Tours",
    "SITE_SUBHEADER": "Website dashboard",
    "SITE_URL": "/",
    "SITE_SYMBOL": "landscape",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "tours.dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "#faf7ef",
            "100": "#f2ead3",
            "200": "#e5d4a6",
            "300": "#d6ba73",
            "400": "#c9a24c",
            "500": "#b08732",
            "600": "#946c27",
            "700": "#785422",
            "800": "#634521",
            "900": "#533a1f",
            "950": "#2f1f0e",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Overview",
                "items": [
                    {"title": "Dashboard", "icon": "dashboard", "link": reverse_lazy("admin:index")},
                    {"title": "View website", "icon": "open_in_new", "link": "/"},
                ],
            },
            {
                "title": "Bookings",
                "items": [
                    {"title": "Enquiries & bookings", "icon": "mail", "link": reverse_lazy("admin:tours_enquiry_changelist")},
                    {"title": "Group departures", "icon": "groups", "link": reverse_lazy("admin:tours_groupdeparture_changelist")},
                ],
            },
            {
                "title": "Tours",
                "items": [
                    {"title": "Tour packages", "icon": "travel_explore", "link": reverse_lazy("admin:tours_tour_changelist")},
                    {"title": "Categories", "icon": "category", "link": reverse_lazy("admin:tours_category_changelist")},
                ],
            },
            {
                "title": "Website content",
                "items": [
                    {"title": "Site settings", "icon": "settings", "link": reverse_lazy("admin:tours_sitesettings_changelist")},
                    {"title": "Pages & guides", "icon": "article", "link": reverse_lazy("admin:tours_page_changelist")},
                    {"title": "FAQs", "icon": "help", "link": reverse_lazy("admin:tours_faq_changelist")},
                    {"title": "Reviews", "icon": "reviews", "link": reverse_lazy("admin:tours_testimonial_changelist")},
                ],
            },
            {
                "title": "Users",
                "items": [
                    {"title": "Admin users", "icon": "person", "link": reverse_lazy("admin:auth_user_changelist")},
                ],
            },
        ],
    },
}
