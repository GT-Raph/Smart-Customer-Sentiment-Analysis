"""Django settings for the self-hosted dashboard.

All deployment-specific values come from environment variables. See the root
``.env.example`` file.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def database_from_mysql_env() -> dict[str, object]:
    """Build the XAMPP MySQL/MariaDB configuration from discrete values."""

    port = os.getenv("MYSQL_PORT", "3306")
    try:
        int(port)
    except ValueError as exc:
        raise RuntimeError("MYSQL_PORT must be an integer") from exc

    engine = (
        "emotion_dashboard.xampp_mysql"
        if env_bool("XAMPP_ALLOW_MARIADB_10_4", False)
        else "django.db.backends.mysql"
    )

    return {
        "ENGINE": engine,
        "NAME": os.getenv("MYSQL_DATABASE", "smart_sentiment"),
        "USER": os.getenv("MYSQL_USER", "root"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": port,
        # XAMPP is commonly stopped/restarted during local development. Do not
        # reuse a connection that belonged to the previous MariaDB process.
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "0")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }


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
    "monitor",
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

DATABASE_ENGINE = os.getenv(
    "DATABASE_ENGINE",
    "mysql",
).strip().lower()
if DATABASE_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif DATABASE_ENGINE in {"mysql", "mariadb", "xampp"}:
    DATABASES = {"default": database_from_mysql_env()}
else:
    raise RuntimeError("DATABASE_ENGINE must be 'mysql' or 'sqlite'")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [path for path in [BASE_DIR / "static"] if path.exists()]

# Raw biometric images are not exposed through Django. The API/worker stores
# them in private storage and deletes them by default after processing.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

captured_faces_value = os.getenv("CAPTURED_FACES_DIR", "private_uploads")
if os.name == "nt" and captured_faces_value.startswith("/"):
    captured_faces_value = "private_uploads"
CAPTURED_FACES_ROOT = Path(captured_faces_value)
if not CAPTURED_FACES_ROOT.is_absolute():
    CAPTURED_FACES_ROOT = BASE_DIR.parent / CAPTURED_FACES_ROOT
CAPTURED_FACES_ROOT = CAPTURED_FACES_ROOT.resolve()

AUTH_USER_MODEL = "monitor.CustomUser"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

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
