"""Runtime configuration for the multi-bank ingestion API.

No credentials belong in source control. Copy ``.env.example`` to ``.env`` for
local development and provide real values through the deployment platform in
production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, quote, unquote, urlparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(os.getenv("APP_ENV_FILE", str(PROJECT_ROOT / ".env"))).expanduser()
load_dotenv(ENV_FILE)


def _as_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _as_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc


def database_url_from_environment(
    environment: Mapping[str, str] | None = None,
) -> str:
    env = os.environ if environment is None else environment
    database_url = env.get("SUPABASE_DB_URL", "").strip() or env.get(
        "DATABASE_URL", ""
    ).strip()
    if database_url:
        parsed = urlparse(database_url)
        if (
            parsed.hostname
            and parsed.hostname.endswith(("supabase.co", "supabase.com"))
            and "sslmode=" not in parsed.query
        ):
            separator = "&" if parsed.query else "?"
            database_url = f"{database_url}{separator}sslmode=require"
        return database_url

    engine = env.get("DB_ENGINE", "postgresql").strip().lower()
    if engine not in {"postgres", "postgresql", "django.db.backends.postgresql"}:
        raise RuntimeError("DB_ENGINE must be PostgreSQL on the SaaS main branch")

    aliases = {
        "SUPABASE_DB_NAME": "DB_NAME",
        "SUPABASE_DB_USER": "DB_USER",
        "SUPABASE_DB_PASSWORD": "DB_PASSWORD",
        "SUPABASE_DB_HOST": "DB_HOST",
        "SUPABASE_DB_PORT": "DB_PORT",
    }
    values = {
        name: (env.get(name) or env.get(alias, "")).strip()
        for name, alias in aliases.items()
    }
    values["SUPABASE_DB_PASSWORD"] = env.get("SUPABASE_DB_PASSWORD") or env.get(
        "DB_PASSWORD", ""
    )
    if not any(values.values()):
        return ""
    missing = [
        aliases[name]
        for name, value in values.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Incomplete Supabase database configuration; missing " + ", ".join(missing)
        )
    try:
        port = int(values["SUPABASE_DB_PORT"])
    except ValueError as exc:
        raise RuntimeError("SUPABASE_DB_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("SUPABASE_DB_PORT must be between 1 and 65535")

    sslmode = (
        env.get("SUPABASE_DB_SSLMODE") or env.get("DB_SSLMODE", "require")
    ).strip() or "require"
    user = quote(values["SUPABASE_DB_USER"], safe="")
    password = quote(values["SUPABASE_DB_PASSWORD"], safe="")
    database = quote(values["SUPABASE_DB_NAME"], safe="")
    return (
        f"postgresql://{user}:{password}@{values['SUPABASE_DB_HOST']}:{port}/"
        f"{database}?sslmode={quote(sslmode, safe='')}"
    )


@dataclass(frozen=True)
class Settings:
    database_url: str = database_url_from_environment()
    max_upload_bytes: int = _as_int("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "ArcFace")
    match_threshold: float = _as_float("MATCH_THRESHOLD", 0.45)

    def validate(self) -> None:
        if not self.database_url:
            raise RuntimeError(
                "Supabase database configuration is required. Set the DB_* "
                "variables or SUPABASE_DB_URL in .env."
            )
        parsed = urlparse(self.database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise RuntimeError("The ingestion API requires a PostgreSQL database URL")
        try:
            parsed.port
        except ValueError as exc:
            raise RuntimeError(
                "The database URL contains an invalid port. URL-encode special "
                "characters in the password."
            ) from exc
        if not parsed.hostname or not parsed.username or not parsed.path.lstrip("/"):
            raise RuntimeError("The PostgreSQL database URL is incomplete")
        if self.max_upload_bytes < 1024:
            raise RuntimeError("MAX_UPLOAD_BYTES is unreasonably small")


settings = Settings()


def _psycopg2_config() -> dict[str, object]:
    if not settings.database_url:
        raise RuntimeError(
            "Supabase database configuration is required. Set the DB_* "
            "variables in .env."
        )
    parsed = urlparse(settings.database_url)
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be an integer") from exc
    query = parse_qs(parsed.query)
    return {
        "dbname": unquote(parsed.path.lstrip("/")),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname or "",
        "port": str(port),
        "connect_timeout": max(1, min(_as_int("DB_CONNECT_TIMEOUT_SECONDS", 10), 60)),
        "sslmode": query.get("sslmode", [os.getenv("DB_SSLMODE", "require")])[0],
    }


def db_config() -> dict[str, object]:
    """Build psycopg settings only when a connection is requested."""
    return _psycopg2_config()


def captured_faces_root() -> Path:
    """Resolve private image storage only when an upload needs it."""
    return Path(
        os.getenv(
            "CAPTURED_FACES_ROOT",
            str(PROJECT_ROOT / "captured_faces"),
        )
    ).expanduser().resolve()


EMBEDDING_MODEL = settings.embedding_model
MATCH_THRESHOLD = settings.match_threshold
MAX_UPLOAD_BYTES = settings.max_upload_bytes
MAX_EMBEDDING_CANDIDATES = max(
    1,
    _as_int("MAX_EMBEDDING_CANDIDATES", 5000),
)
FACE_PROCESSING_CAPACITY_WAIT_SECONDS = max(
    0.1,
    _as_float("FACE_PROCESSING_CAPACITY_WAIT_SECONDS", 2.0),
)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
