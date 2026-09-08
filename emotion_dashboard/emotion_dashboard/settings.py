"""Django settings for the SaaS dashboard.

All deployment-specific values come from environment variables. See the root
``.env.example`` file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = Path(os.getenv("APP_ENV_FILE", str(PROJECT_ROOT / ".env"))).expanduser()
load_dotenv(ENV_FILE)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def database_from_url(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme in {"sqlite", "sqlite3"}:
        path = unquote(parsed.path)
        if os.name == "nt" and re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        if path in {"", "/"}:
            path = str(BASE_DIR / "db.sqlite3")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": path}
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("SUPABASE_DB_URL/DATABASE_URL must be PostgreSQL or SQLite")

    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise RuntimeError(
            "The database URL contains an invalid port. Copy the connection "
            "string from Supabase Connect and URL-encode special characters "
            "in the password."
        ) from exc

    database_name = unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or not parsed.username or not database_name:
        raise RuntimeError("The PostgreSQL database URL is incomplete")

    query = parse_qs(parsed.query)
    options: dict[str, str] = {}
    if "sslmode" in query:
        options["sslmode"] = query["sslmode"][0]
    elif parsed.hostname.endswith(("supabase.co", "supabase.com")):
        options["sslmode"] = "require"

    for option_name in ("sslrootcert", "connect_timeout", "application_name"):
        if option_name in query:
            options[option_name] = query[option_name][0]

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(port),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": options,
    }


def database_from_environment() -> dict[str, object]:
    database_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if database_url:
        return database_from_url(database_url)

    engine = os.getenv("DB_ENGINE", "postgresql").strip().lower()
    if engine not in {"postgres", "postgresql", "django.db.backends.postgresql"}:
        raise RuntimeError("DB_ENGINE must be PostgreSQL on the SaaS main branch")

    names = {
        "NAME": ("SUPABASE_DB_NAME", "DB_NAME"),
        "USER": ("SUPABASE_DB_USER", "DB_USER"),
        "PASSWORD": ("SUPABASE_DB_PASSWORD", "DB_PASSWORD"),
        "HOST": ("SUPABASE_DB_HOST", "DB_HOST"),
        "PORT": ("SUPABASE_DB_PORT", "DB_PORT"),
    }
    supplied = {
        key: (os.getenv(primary) or os.getenv(alias, "")).strip()
        for key, (primary, alias) in names.items()
    }
    supplied["PASSWORD"] = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv(
        "DB_PASSWORD", ""
    )
    if any(supplied.values()):
        missing = [alias for key, (_, alias) in names.items() if not supplied[key]]
        if missing:
            raise RuntimeError(
                "Incomplete Supabase database configuration; missing " + ", ".join(missing)
            )
        try:
            port = int(supplied["PORT"])
        except ValueError as exc:
            raise RuntimeError("DB_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise RuntimeError("DB_PORT must be between 1 and 65535")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": supplied["NAME"],
            "USER": supplied["USER"],
            "PASSWORD": supplied["PASSWORD"],
            "HOST": supplied["HOST"],
            "PORT": str(port),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "sslmode": os.getenv("SUPABASE_DB_SSLMODE")
                or os.getenv("DB_SSLMODE", "require")
            },
        }

    raise RuntimeError(
        "Supabase database configuration is required. Set the DB_* variables "
        "or SUPABASE_DB_URL in .env."
    )


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "development-only-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY is required when DJANGO_DEBUG is false")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "monitor.apps.MonitorConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "emotion_dashboard.urls"
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
                "monitor.context_processors.user_preferences",
            ],
        },
    }
]

WSGI_APPLICATION = "emotion_dashboard.wsgi.application"
ASGI_APPLICATION = "emotion_dashboard.asgi.application"

DATABASES = {"default": database_from_environment()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE") or os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [path for path in [BASE_DIR / "static"] if path.exists()]

# Face images remain outside publicly served static and media paths. Access is
# provided only through the tenant-scoped authenticated snapshot view.
CAPTURED_FACES_ROOT = Path(
    os.getenv("CAPTURED_FACES_ROOT", str(PROJECT_ROOT / "captured_faces"))
).expanduser().resolve()

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "monitor.CustomUser"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
