"""Consent-aware desktop camera client for the ingestion API.

This client intentionally samples at a low rate and uploads only cropped faces.
It is a reference client, not a hidden-surveillance agent. Display an appropriate
notice and obtain consent before use.
"""

from __future__ import annotations

import os
import socket
import time
import uuid
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("INGESTION_API_URL") or os.getenv(
    "FACE_API_URL", "http://127.0.0.1:8001/upload-face"
)
BANK_API_KEY = os.getenv("BANK_API_KEY", "").strip()
BANK_CODE = os.getenv("BANK_CODE", "").strip().upper()
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
MIN_SECONDS_BETWEEN_UPLOADS = float(
    os.getenv("MIN_SECONDS_BETWEEN_UPLOADS")
    or os.getenv("CAPTURE_INTERVAL_SECONDS", "10")
)
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))
LOCAL_QUEUE = Path(os.getenv("LOCAL_CAPTURE_QUEUE", "queued_captures")).resolve()
MAX_QUEUED_IMAGES = int(os.getenv("MAX_QUEUED_IMAGES", "100"))
SESSION_RESET_SECONDS = float(os.getenv("SESSION_RESET_SECONDS", "30"))

OPENCV_FACE_DETECTOR_AVAILABLE = (
    hasattr(cv2, "data")
    and hasattr(cv2, "CascadeClassifier")
)
CASCADE_PATH = (
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if OPENCV_FACE_DETECTOR_AVAILABLE
    else ""
)
FACE_CASCADE = (
    cv2.CascadeClassifier(CASCADE_PATH)
    if OPENCV_FACE_DETECTOR_AVAILABLE
    else None
)


def validate_config() -> None:
    if not BANK_CODE:
        raise RuntimeError("BANK_CODE is required")
    if not BANK_API_KEY:
        raise RuntimeError("BANK_API_KEY is required")
    if FACE_CASCADE is None or FACE_CASCADE.empty():
        raise RuntimeError(
            "OpenCV face detection is unavailable. Stop running Python "
            "processes and reinstall the project requirements."
        )
    LOCAL_QUEUE.mkdir(parents=True, exist_ok=True)


def upload_image(jpeg_bytes: bytes, session_id: str) -> str:
    try:
        response = requests.post(
            API_URL,
            headers={"X-Bank-Code": BANK_CODE, "X-API-Key": BANK_API_KEY},
            files={"file": ("face.jpg", jpeg_bytes, "image/jpeg")},
            data={"pc_name": socket.gethostname().strip().upper()},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        return "retry"
    if 200 <= response.status_code < 300:
        return "success"
    if response.status_code == 401:
        raise RuntimeError("The bank API credentials were rejected")
    if response.status_code in {408, 429} or response.status_code >= 500:
        return "retry"

    print(
        "Capture permanently rejected by the API "
        f"(HTTP {response.status_code}); skipping it."
    )
    return "reject"


def queue_locally(jpeg_bytes: bytes, session_id: str) -> None:
    files = sorted(LOCAL_QUEUE.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    while len(files) >= MAX_QUEUED_IMAGES:
        files.pop(0).unlink(missing_ok=True)
    filename = f"{session_id}__{socket.gethostname()}_{time.time_ns()}.jpg"
    (LOCAL_QUEUE / filename).write_bytes(jpeg_bytes)


def flush_queue() -> None:
    for path in sorted(LOCAL_QUEUE.glob("*.jpg"), key=lambda p: p.stat().st_mtime):
        try:
            session_id = path.name.split("__", 1)[0]
            result = upload_image(path.read_bytes(), session_id)
            if result in {"success", "reject"}:
                path.unlink(missing_ok=True)
            else:
                break
        except requests.RequestException:
            break


def largest_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.15,
        minNeighbors=6,
        minSize=(80, 80),
    )
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda item: item[2] * item[3])
    margin = int(max(w, h) * 0.15)
    x1, y1 = max(0, x - margin), max(0, y - margin)
    x2, y2 = min(frame.shape[1], x + w + margin), min(frame.shape[0], y + h + margin)
    return frame[y1:y2, x1:x2]


def run() -> None:
    validate_config()
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        raise RuntimeError("Camera could not be opened")

    last_upload = 0.0
    last_face_seen = 0.0
    current_session_id: str | None = None
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                time.sleep(1)
                continue

            now = time.monotonic()
            if now - last_upload < MIN_SECONDS_BETWEEN_UPLOADS:
                time.sleep(0.1)
                continue

            face = largest_face(frame)
            if face is None:
                if current_session_id and now - last_face_seen > SESSION_RESET_SECONDS:
                    current_session_id = None
                time.sleep(0.2)
                continue

            last_face_seen = now
            if current_session_id is None:
                current_session_id = uuid.uuid4().hex

            encoded, jpeg = cv2.imencode(".jpg", face, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if not encoded:
                continue

            payload = jpeg.tobytes()
            try:
                flush_queue()
                result = upload_image(payload, current_session_id)
                if result == "retry":
                    queue_locally(payload, current_session_id)
            except requests.RequestException:
                queue_locally(payload, current_session_id)

            last_upload = now
    finally:
        camera.release()


if __name__ == "__main__":
    run()
