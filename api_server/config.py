"""Runtime configuration for the ingestion API and inference worker.

No credentials belong in source control. Copy ``.env.example`` to ``.env`` for
local development and provide real values through the deployment platform in
production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import quote, urlparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(os.getenv("APP_ENV_FILE", str(PROJECT_ROOT / ".env"))).expanduser()
load_dotenv(ENV_FILE)


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def _captured_faces_dir() -> Path:
    default = PROJECT_ROOT / "private_uploads"
    configured = os.getenv("CAPTURED_FACES_DIR", str(default)).strip()
    # /data/private_uploads is the Docker volume path. On Windows, pathlib
    # interprets it as C:\data\private_uploads, which is usually not writable.
    if os.name == "nt" and configured.replace("\\", "/").startswith("/data/"):
        return default.resolve()
    return Path(configured).expanduser().resolve()


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

    field_names = (
        "SUPABASE_DB_NAME",
        "SUPABASE_DB_USER",
        "SUPABASE_DB_PASSWORD",
        "SUPABASE_DB_HOST",
        "SUPABASE_DB_PORT",
    )
    values = {name: env.get(name, "").strip() for name in field_names}
    values["SUPABASE_DB_PASSWORD"] = env.get("SUPABASE_DB_PASSWORD", "")
    if not any(values.values()):
        return ""
    missing = [name for name, value in values.items() if not value]
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

    sslmode = env.get("SUPABASE_DB_SSLMODE", "require").strip() or "require"
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
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    captured_faces_dir: Path = _captured_faces_dir()

    api_key_header: str = "X-API-Key"
    max_upload_bytes: int = _as_int("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
    max_image_pixels: int = _as_int("MAX_IMAGE_PIXELS", 16_000_000)
    rate_limit_per_minute: int = _as_int("RATE_LIMIT_PER_MINUTE", 60)
    job_timeout_seconds: int = _as_int("JOB_TIMEOUT_SECONDS", 300)
    enable_dev_image_endpoint: bool = _as_bool("ENABLE_DEV_IMAGE_ENDPOINT", False)

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "ArcFace")
    match_threshold: float = _as_float("MATCH_THRESHOLD", 0.45)
    enable_face_identification: bool = _as_bool("ENABLE_FACE_IDENTIFICATION", False)
    delete_raw_image_after_processing: bool = _as_bool(
        "DELETE_RAW_IMAGE_AFTER_PROCESSING", True
    )

    def validate(self) -> None:
        if not self.database_url:
            raise RuntimeError(
                "Supabase database configuration is required. Set SUPABASE_DB_URL "
                "or the SUPABASE_DB_* variables in .env."
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
        if not self.redis_url:
            raise RuntimeError("REDIS_URL is required")
        if self.max_upload_bytes < 1024:
            raise RuntimeError("MAX_UPLOAD_BYTES is unreasonably small")
        if self.rate_limit_per_minute < 1:
            raise RuntimeError("RATE_LIMIT_PER_MINUTE must be positive")


settings = Settings()
settings.captured_faces_dir.mkdir(parents=True, exist_ok=True)
