"""Django settings for WeighingMS (local training build)."""

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

SRC_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SRC_DIR.parent

# Local training build only; never deployed.
SECRET_KEY = "django-insecure-weighingms-local-training-only"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "orgatex",
    "devices",
    "batches",
    "weighing",
    "station",
    "dummy_orgatex",
    "dummy_scale",
    "dummy_scanner",
    "dummy_printer",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "weighingms.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": ["django.template.context_processors.request"]
        },
    },
]

WSGI_APPLICATION = "weighingms.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # WEIGHINGMS_DB_PATH lets the Playwright server use its own database.
        "NAME": os.environ.get("WEIGHINGMS_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# OrgaTEX integration (NFR-13: change without code). Points at the Dummy
# OrgaTEX training contract served by this same dev server.
ORGATEX_BASE_URL = os.environ.get("ORGATEX_BASE_URL", "http://localhost:8000/api")
ORGATEX_TIMEOUT_SECONDS = float(os.environ.get("ORGATEX_TIMEOUT_SECONDS", "5"))

# Device integrations (NFR-13). Point at the Dummy Scale / Scanner training
# contracts on this dev server. The timeout stays below the 2 s target for
# detecting a disconnected scale (IR-13).
SCALE_BASE_URL = os.environ.get("SCALE_BASE_URL", "http://localhost:8000/api")
SCANNER_BASE_URL = os.environ.get("SCANNER_BASE_URL", "http://localhost:8000/api")
DEVICE_TIMEOUT_SECONDS = float(os.environ.get("DEVICE_TIMEOUT_SECONDS", "2"))

# Operator terminal (NFR-13): the station name shown in the header.
STATION_NAME = os.environ.get("STATION_NAME", "STATION 01")


def positive_decimal(name: str, default: str) -> Decimal:
    """A positive, finite Decimal from the environment; fail at startup otherwise."""
    text = os.environ.get(name, default)
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite() or value <= 0:
        raise ImproperlyConfigured(f"{name} must be a positive number, got {text!r}")
    return value


# Weighing rules (FR-8, NFR-13): target ≤ threshold → 3 kg precision scale,
# above → 32 kg floor scale. Set the environment variable to change it.
WEIGHING_SCALE_THRESHOLD_KG = positive_decimal("WEIGHING_SCALE_THRESHOLD_KG", "3")
