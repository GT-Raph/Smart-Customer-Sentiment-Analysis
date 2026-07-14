from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# API and workstation identity
FACE_API_URL = os.getenv("FACE_API_URL", "http://127.0.0.1:8001/upload-face").strip()
BANK_CODE = os.getenv("BANK_CODE", "").strip().upper()
BANK_API_KEY = os.getenv("BANK_API_KEY", "").strip()
PC_NAME = socket.gethostname().strip().upper()

# Camera
CAMERA_INDEX = env_int("CAMERA_INDEX", 0)
CAMERA_WIDTH = env_int("CAMERA_WIDTH", 1280)
CAMERA_HEIGHT = env_int("CAMERA_HEIGHT", 720)
CAMERA_FPS = env_int("CAMERA_FPS", 30)
REQUEST_TIMEOUT_SECONDS = env_int("REQUEST_TIMEOUT_SECONDS", 90)
PREVIEW_ENABLED = env_bool("PREVIEW_ENABLED", True)
UPLOAD_FACE_CROP = env_bool("UPLOAD_FACE_CROP", True)
JPEG_QUALITY = max(60, min(env_int("JPEG_QUALITY", 92), 100))

# Customer-only capture zone, expressed as percentages of the full frame
ROI_LEFT = env_float("ROI_LEFT", 0.18)
ROI_TOP = env_float("ROI_TOP", 0.06)
ROI_RIGHT = env_float("ROI_RIGHT", 0.82)
ROI_BOTTOM = env_float("ROI_BOTTOM", 0.96)

# Quality gate
MIN_FACE_WIDTH_PIXELS = env_int("MIN_FACE_WIDTH_PIXELS", 120)
MIN_FACE_HEIGHT_PIXELS = env_int("MIN_FACE_HEIGHT_PIXELS", 120)
MIN_FACE_AREA_RATIO = env_float("MIN_FACE_AREA_RATIO", 0.035)
BLUR_THRESHOLD = env_float("BLUR_THRESHOLD", 45.0)
MIN_BRIGHTNESS = env_float("MIN_BRIGHTNESS", 45.0)
MAX_BRIGHTNESS = env_float("MAX_BRIGHTNESS", 215.0)
MAX_DARK_PIXEL_PERCENT = env_float("MAX_DARK_PIXEL_PERCENT", 0.58)
MAX_BRIGHT_PIXEL_PERCENT = env_float("MAX_BRIGHT_PIXEL_PERCENT", 0.38)

# Stability and duplicate prevention
STABLE_FRAMES_REQUIRED = max(2, env_int("STABLE_FRAMES_REQUIRED", 6))
STABILITY_IOU_THRESHOLD = env_float("STABILITY_IOU_THRESHOLD", 0.55)
SAMPLE_WINDOW_SECONDS = env_float("SAMPLE_WINDOW_SECONDS", 1.2)
MIN_GOOD_CANDIDATES = max(1, env_int("MIN_GOOD_CANDIDATES", 4))
DETECTION_INTERVAL_FRAMES = max(1, env_int("DETECTION_INTERVAL_FRAMES", 2))
FACE_ABSENCE_RESET_SECONDS = env_float("FACE_ABSENCE_RESET_SECONDS", 1.8)
CAPTURE_COOLDOWN_SECONDS = env_float("CAPTURE_COOLDOWN_SECONDS", 5.0)

# Offline queue
OFFLINE_QUEUE_DIR = ROOT / os.getenv("OFFLINE_QUEUE_DIR", "offline_queue")
QUEUE_RETRY_INTERVAL_SECONDS = env_float("QUEUE_RETRY_INTERVAL_SECONDS", 30.0)
MAX_OFFLINE_QUEUE_FILES = max(10, env_int("MAX_OFFLINE_QUEUE_FILES", 300))

WINDOW_NAME = "Customer Capture Setup"
Box = tuple[int, int, int, int]

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
EYE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
)

if FACE_CASCADE.empty():
    raise RuntimeError("OpenCV could not load the frontal-face detector.")


@dataclass
class Quality:
    accepted: bool
    score: float
    blur: float
    brightness: float
    eye_count: int
    face_area_ratio: float
    reason: str


@dataclass
class Candidate:
    frame: np.ndarray
    face_crop: np.ndarray
    quality: Quality


# -----------------------------------------------------------------------------
# Camera and face analysis
# -----------------------------------------------------------------------------


def validate_settings() -> None:
    missing = []
    if not BANK_CODE:
        missing.append("BANK_CODE")
    if not BANK_API_KEY:
        missing.append("BANK_API_KEY")
    if not FACE_API_URL:
        missing.append("FACE_API_URL")
    if missing:
        raise RuntimeError("Missing .env value(s): " + ", ".join(missing))
    if not (0 <= ROI_LEFT < ROI_RIGHT <= 1):
        raise RuntimeError("ROI_LEFT and ROI_RIGHT must be between 0 and 1.")
    if not (0 <= ROI_TOP < ROI_BOTTOM <= 1):
        raise RuntimeError("ROI_TOP and ROI_BOTTOM must be between 0 and 1.")


def open_camera() -> cv2.VideoCapture:
    capture = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not capture.isOpened():
        capture.release()
        capture = cv2.VideoCapture(CAMERA_INDEX)
    if not capture.isOpened():
        raise RuntimeError(
            f"Camera {CAMERA_INDEX} could not be opened. Close Camera, Teams, "
            "Zoom, WhatsApp and OBS, then retry."
        )

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    capture.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def get_roi(frame: np.ndarray) -> Box:
    height, width = frame.shape[:2]
    x1 = max(0, min(int(width * ROI_LEFT), width - 2))
    y1 = max(0, min(int(height * ROI_TOP), height - 2))
    x2 = max(x1 + 1, min(int(width * ROI_RIGHT), width))
    y2 = max(y1 + 1, min(int(height * ROI_BOTTOM), height))
    return x1, y1, x2 - x1, y2 - y1


def detect_faces(frame: np.ndarray) -> tuple[list[Box], Box]:
    rx, ry, rw, rh = get_roi(frame)
    region = frame[ry : ry + rh, rx : rx + rw]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    minimum = max(80, min(MIN_FACE_WIDTH_PIXELS, int(rw * 0.18)))
    found = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(minimum, minimum),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )

    faces: list[Box] = []
    for x, y, width, height in found:
        if width < MIN_FACE_WIDTH_PIXELS or height < MIN_FACE_HEIGHT_PIXELS:
            continue
        area_ratio = (width * height) / float(max(rw * rh, 1))
        if area_ratio < MIN_FACE_AREA_RATIO:
            continue
        faces.append((rx + int(x), ry + int(y), int(width), int(height)))

    faces.sort(key=lambda box: box[2] * box[3], reverse=True)
    return faces, (rx, ry, rw, rh)


def iou(first: Box, second: Box) -> float:
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


def face_crop_with_margin(frame: np.ndarray, box: Box) -> np.ndarray:
    x, y, width, height = box
    frame_height, frame_width = frame.shape[:2]
    x1 = max(0, x - int(width * 0.28))
    y1 = max(0, y - int(height * 0.38))
    x2 = min(frame_width, x + width + int(width * 0.28))
    y2 = min(frame_height, y + height + int(height * 0.30))
    return frame[y1:y2, x1:x2].copy()


def inspect_quality(frame: np.ndarray, face_box: Box, roi: Box) -> Quality:
    x, y, width, height = face_box
    _, _, roi_width, roi_height = roi
    face = frame[y : y + height, x : x + width]
    if face.size == 0:
        return Quality(False, 0, 0, 0, 0, 0, "Invalid face crop")

    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    dark_percent = float(np.mean(gray < 35))
    bright_percent = float(np.mean(gray > 235))
    area_ratio = (width * height) / float(max(roi_width * roi_height, 1))

    eye_count = 0
    if not EYE_CASCADE.empty():
        upper_face = gray[: max(1, int(height * 0.62)), :]
        eyes = EYE_CASCADE.detectMultiScale(
            upper_face,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(18, 18),
        )
        eye_count = min(len(eyes), 2)

    reason = ""
    if blur < BLUR_THRESHOLD:
        reason = "Hold still - image is blurred"
    elif brightness < MIN_BRIGHTNESS:
        reason = "Face is too dark"
    elif brightness > MAX_BRIGHTNESS:
        reason = "Face is too bright"
    elif dark_percent > MAX_DARK_PIXEL_PERCENT:
        reason = "Too many dark facial pixels"
    elif bright_percent > MAX_BRIGHT_PIXEL_PERCENT:
        reason = "Too much glare or overexposure"

    blur_score = min(blur / max(BLUR_THRESHOLD * 4, 1), 1.0)
    exposure_score = max(0.0, 1.0 - abs(brightness - 125.0) / 125.0)
    size_score = min(area_ratio / 0.18, 1.0)
    eye_score = eye_count / 2.0
    score = blur_score * 0.42 + exposure_score * 0.33 + size_score * 0.20 + eye_score * 0.05

    return Quality(
        accepted=not reason,
        score=round(score, 4),
        blur=round(blur, 1),
        brightness=round(brightness, 1),
        eye_count=eye_count,
        face_area_ratio=round(area_ratio, 4),
        reason=reason,
    )


# -----------------------------------------------------------------------------
# Upload and offline queue
# -----------------------------------------------------------------------------


def encode_jpeg(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(
        ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    )
    if not success:
        raise RuntimeError("Could not encode the selected camera frame.")
    return encoded.tobytes()


def api_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        return str(payload.get("detail", payload)) if isinstance(payload, dict) else str(payload)
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"


def send_to_api(image_bytes: bytes, filename: str) -> tuple[str, str, Optional[dict]]:
    try:
        response = requests.post(
            FACE_API_URL,
            headers={"X-Bank-Code": BANK_CODE, "X-API-Key": BANK_API_KEY},
            files={"file": (filename, image_bytes, "image/jpeg")},
            data={"pc_name": PC_NAME},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        return "retry", str(error), None

    detail = api_error(response)
    if 200 <= response.status_code < 300:
        try:
            return "success", detail, response.json()
        except ValueError:
            return "success", detail, None
    if response.status_code in {400, 401, 403, 404}:
        return "reject", detail, None
    return "retry", f"HTTP {response.status_code}: {detail}", None


def safe_component(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in value)


def new_filename() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
    return f"{safe_component(BANK_CODE)}_{safe_component(PC_NAME)}_{stamp}.jpg"


def trim_queue() -> None:
    images = sorted(OFFLINE_QUEUE_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    for path in images[: max(0, len(images) - MAX_OFFLINE_QUEUE_FILES)]:
        path.unlink(missing_ok=True)
        path.with_suffix(".json").unlink(missing_ok=True)


def queue_image(image_bytes: bytes, filename: str, error: str, quality: Quality) -> None:
    OFFLINE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    image_path = OFFLINE_QUEUE_DIR / filename
    image_path.write_bytes(image_bytes)
    image_path.with_suffix(".json").write_text(
        json.dumps(
            {
                "bank_code": BANK_CODE,
                "pc_name": PC_NAME,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_error": error,
                "blur": quality.blur,
                "brightness": quality.brightness,
                "quality_score": quality.score,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    trim_queue()
    print(f"Image saved to offline queue: {filename}")


def print_result(payload: Optional[dict]) -> None:
    if not payload:
        return
    branch = payload.get("branch")
    if isinstance(branch, dict):
        print(f"Assigned branch: {branch.get('name')} ({branch.get('code')})")
    faces = payload.get("faces")
    if isinstance(faces, list):
        for face in faces:
            if isinstance(face, dict):
                print(
                    f"Emotion: {face.get('emotion', 'unknown')} "
                    f"({face.get('confidence', 0)}%)"
                )
    elif not branch:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


def upload_candidate(candidate: Candidate) -> None:
    image = candidate.face_crop if UPLOAD_FACE_CROP else candidate.frame
    image_bytes = encode_jpeg(image)
    filename = new_filename()
    status, detail, payload = send_to_api(image_bytes, filename)

    if status == "success":
        print("Capture uploaded successfully.")
        print_result(payload)
    elif status == "retry":
        print(f"The face API could not process the capture: {detail}")
        queue_image(image_bytes, filename, detail, candidate.quality)
    else:
        print("UPLOAD REJECTED:")
        print(detail)
        print(f"Bank: {BANK_CODE} | Windows PC name: {PC_NAME}")


def retry_offline_queue() -> None:
    OFFLINE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    images = sorted(OFFLINE_QUEUE_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    if not images:
        return

    print(f"Retrying {len(images)} offline image(s)...")
    for image_path in images:
        status, detail, payload = send_to_api(image_path.read_bytes(), image_path.name)
        if status == "success":
            image_path.unlink(missing_ok=True)
            image_path.with_suffix(".json").unlink(missing_ok=True)
            print(f"Queued image uploaded: {image_path.name}")
            print_result(payload)
        elif status == "reject":
            print(f"Queued image rejected and left for review: {image_path.name} — {detail}")
        else:
            print(f"Face API is not ready: {detail}")
            break


# -----------------------------------------------------------------------------
# Preview
# -----------------------------------------------------------------------------


def put_text(frame: np.ndarray, text: str, position: tuple[int, int], color, scale=0.55):
    cv2.putText(
        frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA
    )


def build_preview(
    frame: np.ndarray,
    roi: Box,
    faces: list[Box],
    quality: Optional[Quality],
    message: str,
    stable_count: int,
    waiting_for_departure: bool,
) -> np.ndarray:
    preview = frame.copy()
    rx, ry, rw, rh = roi
    cv2.rectangle(preview, (rx, ry), (rx + rw, ry + rh), (255, 210, 70), 2)

    for x, y, width, height in faces:
        color = (70, 70, 255) if len(faces) > 1 else (0, 190, 255)
        if len(faces) == 1 and quality and quality.accepted:
            color = (70, 220, 120)
        cv2.rectangle(preview, (x, y), (x + width, y + height), color, 2)
        if quality:
            put_text(
                preview,
                f"Blur {quality.blur:.0f} | Light {quality.brightness:.0f} | Score {quality.score:.2f}",
                (x, max(100, y - 10)),
                color,
                0.45,
            )

    overlay = preview.copy()
    cv2.rectangle(overlay, (0, 0), (preview.shape[1], 82), (10, 14, 22), -1)
    cv2.addWeighted(overlay, 0.82, preview, 0.18, 0, preview)
    put_text(preview, message[:110], (18, 30), (70, 220, 120), 0.58)

    second_line = (
        f"Bank {BANK_CODE} | PC {PC_NAME} | Stable {stable_count}/{STABLE_FRAMES_REQUIRED}"
    )
    if waiting_for_departure:
        second_line += " | Waiting for customer to leave"
    put_text(preview, second_line, (18, 60), (190, 200, 220), 0.45)
    put_text(preview, "Customer capture zone", (rx + 8, max(108, ry + 24)), (255, 210, 70), 0.45)
    return preview


# -----------------------------------------------------------------------------
# Main service
# -----------------------------------------------------------------------------


def run() -> None:
    validate_settings()
    OFFLINE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    camera = open_camera()

    print("=" * 64)
    print("Customer sentiment capture service started")
    print(f"Bank code: {BANK_CODE}")
    print(f"Actual Windows PC name: {PC_NAME}")
    print(f"API address: {FACE_API_URL}")
    print(f"Customer-only face crop upload: {UPLOAD_FACE_CROP}")
    print("The branch will be selected automatically from the PC name.")
    print("Press Q or Esc in the preview window to stop.")
    print("=" * 64)

    frame_number = 0
    last_box: Optional[Box] = None
    stable_count = 0
    stable_started_at: Optional[float] = None
    candidates: list[Candidate] = []
    waiting_for_departure = False
    no_face_started_at: Optional[float] = None
    last_capture_at = 0.0
    next_queue_retry = time.monotonic() + 2.0

    last_faces: list[Box] = []
    last_roi: Optional[Box] = None
    last_quality: Optional[Quality] = None
    message = "Waiting for one customer inside the capture zone"

    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                time.sleep(0.1)
                continue

            now = time.monotonic()
            frame_number += 1

            if now >= next_queue_retry:
                retry_offline_queue()
                next_queue_retry = now + QUEUE_RETRY_INTERVAL_SECONDS

            if frame_number % DETECTION_INTERVAL_FRAMES == 0:
                faces, roi = detect_faces(frame)
                last_faces, last_roi, last_quality = faces, roi, None

                if waiting_for_departure:
                    if faces:
                        no_face_started_at = None
                        message = "Captured - waiting for customer to leave"
                    else:
                        if no_face_started_at is None:
                            no_face_started_at = now
                        if now - no_face_started_at >= FACE_ABSENCE_RESET_SECONDS:
                            waiting_for_departure = False
                            no_face_started_at = None
                            last_box = None
                            stable_count = 0
                            stable_started_at = None
                            candidates.clear()
                            message = "Ready for the next customer"
                        else:
                            message = "Customer left - resetting capture"

                elif len(faces) == 0:
                    last_box = None
                    stable_count = 0
                    stable_started_at = None
                    candidates.clear()
                    message = "Waiting for one customer inside the capture zone"

                elif len(faces) > 1:
                    last_box = None
                    stable_count = 0
                    stable_started_at = None
                    candidates.clear()
                    message = "Multiple faces detected - keep only one customer in the zone"

                else:
                    face_box = faces[0]
                    quality = inspect_quality(frame, face_box, roi)
                    last_quality = quality

                    if last_box and iou(last_box, face_box) >= STABILITY_IOU_THRESHOLD:
                        stable_count += 1
                    else:
                        stable_count = 1
                        stable_started_at = now
                        candidates.clear()
                    last_box = face_box

                    if not quality.accepted:
                        candidates.clear()
                        message = quality.reason
                    elif stable_count < STABLE_FRAMES_REQUIRED:
                        message = f"Face found - hold position briefly ({stable_count}/{STABLE_FRAMES_REQUIRED})"
                    else:
                        candidates.append(
                            Candidate(
                                frame=frame.copy(),
                                face_crop=face_crop_with_margin(frame, face_box),
                                quality=quality,
                            )
                        )
                        candidates = sorted(
                            candidates, key=lambda item: item.quality.score, reverse=True
                        )[:12]
                        message = f"Good face - selecting best frame ({len(candidates)}/{MIN_GOOD_CANDIDATES})"

                        stable_time = now - stable_started_at if stable_started_at else 0
                        ready = (
                            len(candidates) >= MIN_GOOD_CANDIDATES
                            and stable_time >= SAMPLE_WINDOW_SECONDS
                            and now - last_capture_at >= CAPTURE_COOLDOWN_SECONDS
                        )
                        if ready:
                            upload_candidate(candidates[0])
                            last_capture_at = now
                            waiting_for_departure = True
                            no_face_started_at = None
                            last_box = None
                            stable_count = 0
                            stable_started_at = None
                            candidates.clear()
                            message = "Captured - waiting for customer to leave"

            if PREVIEW_ENABLED:
                preview = build_preview(
                    frame,
                    last_roi or get_roi(frame),
                    last_faces,
                    last_quality,
                    message,
                    stable_count,
                    waiting_for_departure,
                )
                cv2.imshow(WINDOW_NAME, preview)
                key = cv2.waitKey(1) & 0xFF
                if key in {ord("q"), 27}:
                    break
            else:
                time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("Capture service stopped.")


if __name__ == "__main__":
    run()