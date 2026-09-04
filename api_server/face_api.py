"""Authenticated image-ingestion API.

The API validates and stores uploads, records a queued job, and delegates all
model work to an RQ worker. It does not load TensorFlow/DeepFace itself.
"""

from __future__ import annotations

import logging
import os
import secrets
import re
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import ulid
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from redis import Redis
from rq import Queue

from .config import settings
from .db_utils import (
    DeviceContext,
    QuotaExceeded,
    authenticate_device,
    database_is_ready,
    get_snapshot_for_device,
    insert_snapshot,
    mark_failed,
)

logger = logging.getLogger("face_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="Smart Customer Sentiment Ingestion API",
    version="2.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") != "production" else None,
    redoc_url=None,
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def redis_connection() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=False)


def job_queue() -> Queue:
    return Queue("face_jobs", connection=redis_connection())


def _extract_token(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return None


def _rate_limit(device_id: int) -> None:
    redis = redis_connection()
    key = f"rate:upload:{device_id}"
    try:
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Upload rate limit exceeded")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Rate-limit backend unavailable: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from exc


async def require_device(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> DeviceContext:
    token = _extract_token(x_api_key, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device API key",
        )

    device = authenticate_device(token)
    if not device:
        # Constant-time dummy comparison reduces observable differences.
        secrets.compare_digest(token, "invalid-device-token")
        raise HTTPException(status_code=401, detail="Invalid device API key")
    return device


@app.on_event("startup")
def validate_startup() -> None:
    settings.validate()
    if not database_is_ready():
        raise RuntimeError("Database schema is unavailable. Run Django migrations first.")
    try:
        redis_connection().ping()
    except Exception as exc:
        raise RuntimeError("Redis is unavailable") from exc


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "sentiment-ingestion", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    database_status = "ok" if database_is_ready() else "unavailable"
    try:
        redis_status = "ok" if redis_connection().ping() else "unavailable"
    except Exception:
        redis_status = "unavailable"

    if database_status != "ok" or redis_status != "ok":
        raise HTTPException(
            status_code=503,
            detail={"database": database_status, "redis": redis_status},
        )
    return {"status": "ok", "database": database_status, "redis": redis_status}


@app.post("/v1/snapshots", status_code=202)
@app.post("/upload-face", status_code=202, include_in_schema=False)
async def upload_face(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    device: DeviceContext = Depends(require_device),
) -> dict[str, object]:
    _rate_limit(device.id)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    data = await file.read(settings.max_upload_bytes + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds upload limit")

    expected_formats = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
    }
    try:
        Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            image_format = image.format
            if image_format != expected_formats[file.content_type]:
                raise HTTPException(status_code=400, detail="Image type does not match its content")
            if width < 32 or height < 32:
                raise HTTPException(status_code=400, detail="Image is too small")
            if width * height > settings.max_image_pixels:
                raise HTTPException(status_code=413, detail="Image dimensions exceed limit")
            image.verify()
    except HTTPException:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise HTTPException(status_code=400, detail="Invalid image")

    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    job_id = str(ulid.new())
    normalized_session_id = session_id or job_id
    if not SESSION_ID_PATTERN.fullmatch(normalized_session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    final_path = settings.captured_faces_dir / f"{job_id}.jpg"
    temporary_path = settings.captured_faces_dir / f".{job_id}.tmp"

    encoded, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not encoded:
        raise HTTPException(status_code=500, detail="Could not normalise image")

    snapshot_id: int | None = None
    try:
        temporary_path.write_bytes(jpeg.tobytes())
        temporary_path.replace(final_path)

        snapshot_id = insert_snapshot(
            job_id=job_id,
            device=device,
            image_path=str(final_path),
            content_type="image/jpeg",
            size_bytes=final_path.stat().st_size,
            session_id=normalized_session_id,
        )
        job_queue().enqueue(
            "api_server.worker.process_snapshot",
            snapshot_id,
            job_id=job_id,
            job_timeout=settings.job_timeout_seconds,
            result_ttl=3600,
            failure_ttl=86400,
        )
        return {"job_id": job_id, "status": "queued"}

    except QuotaExceeded as exc:
        final_path.unlink(missing_ok=True)
        temporary_path.unlink(missing_ok=True)
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload queueing failed")
        if snapshot_id is not None:
            try:
                mark_failed(snapshot_id, "QueueUnavailable")
            except Exception:
                logger.exception("Could not mark failed snapshot")
        final_path.unlink(missing_ok=True)
        temporary_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="Could not queue analysis") from exc


@app.get("/v1/snapshots/{job_id}")
def snapshot_status(
    job_id: str,
    device: DeviceContext = Depends(require_device),
) -> dict[str, object]:
    row = get_snapshot_for_device(job_id, device)
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    row.pop("image_path", None)
    return row


@app.get("/v1/snapshots/{job_id}/image", include_in_schema=False)
def snapshot_image(
    job_id: str,
    device: DeviceContext = Depends(require_device),
):
    if not settings.enable_dev_image_endpoint:
        raise HTTPException(status_code=404, detail="Not found")
    row = get_snapshot_for_device(job_id, device)
    if not row or not row.get("image_path"):
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(row["image_path"]).resolve()
    if settings.captured_faces_dir not in path.parents:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)
