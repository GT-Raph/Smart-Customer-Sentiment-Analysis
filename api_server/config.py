"""Runtime configuration for the ingestion API and inference worker.

No credentials belong in source control. Copy ``.env.example`` to ``.env`` for
local development and provide real values through the deployment platform in
production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


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


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    captured_faces_dir: Path = Path(
        os.getenv(
            "CAPTURED_FACES_DIR",
            str(Path(__file__).resolve().parent.parent / "private_uploads"),
        )
    ).resolve()

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
            raise RuntimeError("DATABASE_URL is required")
        if not self.redis_url:
            raise RuntimeError("REDIS_URL is required")
        if self.max_upload_bytes < 1024:
            raise RuntimeError("MAX_UPLOAD_BYTES is unreasonably small")
        if self.rate_limit_per_minute < 1:
            raise RuntimeError("RATE_LIMIT_PER_MINUTE must be positive")


settings = Settings()
settings.captured_faces_dir.mkdir(parents=True, exist_ok=True)
