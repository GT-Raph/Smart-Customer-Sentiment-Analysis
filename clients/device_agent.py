"""Consent-aware desktop camera agent for the ingestion API.

The agent has no live camera preview. It briefly acquires the camera for each
sampling attempt and always releases it before processing or uploading the
frame, allowing other desktop applications to use the camera between samples.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sentiment-grid-device")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

API_URL = os.getenv("INGESTION_API_URL", "http://127.0.0.1:8001/v1/snapshots")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAPTURE_INTERVAL_SECONDS = float(
    os.getenv(
        "CAPTURE_INTERVAL_SECONDS",
        os.getenv("MIN_SECONDS_BETWEEN_UPLOADS", "10"),
    )
)
CAMERA_BUSY_RETRY_SECONDS = float(os.getenv("CAMERA_BUSY_RETRY_SECONDS", "15"))
CAMERA_WARMUP_FRAMES = int(os.getenv("CAMERA_WARMUP_FRAMES", "3"))
CAMERA_WARMUP_DELAY_SECONDS = float(os.getenv("CAMERA_WARMUP_DELAY_SECONDS", "0.08"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))
LOCAL_QUEUE = Path(os.getenv("LOCAL_CAPTURE_QUEUE", "queued_captures")).resolve()
MAX_QUEUED_IMAGES = int(os.getenv("MAX_QUEUED_IMAGES", "100"))
SESSION_RESET_SECONDS = float(os.getenv("SESSION_RESET_SECONDS", "30"))
SHIFT_END_HOUR = int(os.getenv("SHIFT_END_HOUR", "17"))
RESUME_WARNING_SECONDS = float(os.getenv("RESUME_WARNING_SECONDS", "300"))

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)


def _default_state_file() -> Path:
    configured = os.getenv("DEVICE_STATE_FILE")
    if configured:
        path = Path(configured).expanduser()
        return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "SentimentGrid" / "device-agent-state.json"
    return Path.home() / ".sentiment-grid" / "device-agent-state.json"


STATE_FILE = _default_state_file()


@dataclass(frozen=True)
class PauseRecord:
    paused_until: datetime
    reason: str
    requested_at: datetime

    def remaining_seconds(self, now: datetime) -> float:
        return max(0.0, (self.paused_until - now).total_seconds())


class PauseController:
    """Persist finite pause leases so a forgotten pause always expires."""

    def __init__(
        self,
        state_file: Path = STATE_FILE,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.state_file = state_file
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()

    def now(self) -> datetime:
        value = self._now()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _read(self) -> PauseRecord | None:
        with self._lock:
            if not self.state_file.exists():
                return None
            try:
                payload = json.loads(self.state_file.read_text(encoding="utf-8"))
                paused_until = datetime.fromisoformat(payload["paused_until"])
                requested_at = datetime.fromisoformat(payload["requested_at"])
                if paused_until.tzinfo is None:
                    paused_until = paused_until.replace(tzinfo=timezone.utc)
                if requested_at.tzinfo is None:
                    requested_at = requested_at.replace(tzinfo=timezone.utc)
                return PauseRecord(
                    paused_until=paused_until.astimezone(timezone.utc),
                    reason=str(payload.get("reason") or "Manual pause"),
                    requested_at=requested_at.astimezone(timezone.utc),
                )
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                logger.warning("Ignoring an invalid device pause state at %s", self.state_file)
                self.clear()
                return None

    def active(self) -> PauseRecord | None:
        record = self._read()
        if record and record.paused_until <= self.now():
            self.clear()
            return None
        return record

    def pause_for(self, duration: timedelta, reason: str) -> PauseRecord:
        if duration.total_seconds() <= 0:
            raise ValueError("Pause duration must be positive")
        return self.pause_until(self.now() + duration, reason)

    def pause_until(self, paused_until: datetime, reason: str) -> PauseRecord:
        if paused_until.tzinfo is None:
            raise ValueError("Pause expiry must include a timezone")
        now = self.now()
        paused_until = paused_until.astimezone(timezone.utc)
        if paused_until <= now:
            raise ValueError("Pause expiry must be in the future")

        record = PauseRecord(
            paused_until=paused_until,
            reason=reason.strip() or "Manual pause",
            requested_at=now,
        )
        payload = {
            "paused_until": record.paused_until.isoformat(),
            "reason": record.reason,
            "requested_at": record.requested_at.isoformat(),
        }
        with self._lock:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temporary.replace(self.state_file)
        return record

    def clear(self) -> None:
        with self._lock:
            self.state_file.unlink(missing_ok=True)


def validate_config() -> None:
    if not DEVICE_API_KEY:
        raise RuntimeError(
            "DEVICE_API_KEY is required. Create a device key with Django's "
            "create_device_key command, add it to .env, then restart this client."
        )
    if FACE_CASCADE.empty():
        raise RuntimeError("OpenCV face detector could not be loaded")
    if CAPTURE_INTERVAL_SECONDS <= 0:
        raise RuntimeError("CAPTURE_INTERVAL_SECONDS must be positive")
    if CAMERA_BUSY_RETRY_SECONDS <= 0:
        raise RuntimeError("CAMERA_BUSY_RETRY_SECONDS must be positive")
    if CAMERA_WARMUP_FRAMES < 1:
        raise RuntimeError("CAMERA_WARMUP_FRAMES must be at least 1")
    if not 0 <= SHIFT_END_HOUR <= 23:
        raise RuntimeError("SHIFT_END_HOUR must be between 0 and 23")
    LOCAL_QUEUE.mkdir(parents=True, exist_ok=True)


def upload_image(jpeg_bytes: bytes, session_id: str) -> bool:
    response = requests.post(
        API_URL,
        headers={"X-API-Key": DEVICE_API_KEY},
        files={"file": ("face.jpg", jpeg_bytes, "image/jpeg")},
        data={"session_id": session_id},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code == 202:
        return True
    if response.status_code in {401, 403}:
        raise RuntimeError("The device API key was rejected")
    return False


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
            if upload_image(path.read_bytes(), session_id):
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


def capture_frame(
    camera_index: int = CAMERA_INDEX,
    warmup_frames: int = CAMERA_WARMUP_FRAMES,
    warmup_delay_seconds: float = CAMERA_WARMUP_DELAY_SECONDS,
):
    """Capture one frame and release the camera before returning."""
    camera = cv2.VideoCapture(camera_index)
    try:
        if not camera.isOpened():
            return None

        frame = None
        for index in range(max(1, warmup_frames)):
            ok, candidate = camera.read()
            if ok:
                frame = candidate
            if index + 1 < warmup_frames and warmup_delay_seconds > 0:
                time.sleep(warmup_delay_seconds)
        return frame
    finally:
        camera.release()


def _end_of_shift(now: datetime | None = None) -> datetime:
    local_now = now or datetime.now().astimezone()
    if local_now.tzinfo is None:
        local_now = local_now.astimezone()
    end = local_now.replace(hour=SHIFT_END_HOUR, minute=0, second=0, microsecond=0)
    if end <= local_now:
        end += timedelta(days=1)
    return end


class DeviceAgent:
    def __init__(self, pause_controller: PauseController) -> None:
        self.pause_controller = pause_controller
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self._status_lock = threading.Lock()
        self._status = "Starting"
        self._status_detail = ""
        self._notifier: Callable[[str], None] | None = None
        self._status_listener: Callable[[], None] | None = None
        self._resume_warning_for: datetime | None = None

    def set_notifier(self, notifier: Callable[[str], None]) -> None:
        self._notifier = notifier

    def set_status_listener(self, listener: Callable[[], None]) -> None:
        self._status_listener = listener

    def _notify(self, message: str) -> None:
        logger.info(message)
        if self._notifier:
            try:
                self._notifier(message)
            except Exception:
                logger.debug("Desktop notification could not be displayed", exc_info=True)

    def _set_status(self, status: str, detail: str = "") -> None:
        with self._status_lock:
            changed = (status, detail) != (self._status, self._status_detail)
            self._status = status
            self._status_detail = detail
        if changed:
            logger.info("Camera agent status: %s%s", status, f" - {detail}" if detail else "")
            if self._status_listener:
                try:
                    self._status_listener()
                except Exception:
                    logger.debug("Tray status could not be refreshed", exc_info=True)

    def status_text(self) -> str:
        with self._status_lock:
            if self._status_detail:
                return f"{self._status}: {self._status_detail}"
            return self._status

    def pause_for(self, minutes: int, reason: str = "Teller pause") -> PauseRecord:
        record = self.pause_controller.pause_for(timedelta(minutes=minutes), reason)
        self._resume_warning_for = None
        self.wake_event.set()
        local_expiry = record.paused_until.astimezone()
        self._set_status("Paused", f"until {local_expiry:%H:%M}")
        self._notify(f"Face capture paused until {local_expiry:%H:%M}.")
        return record

    def pause_until_end_of_shift(self) -> PauseRecord:
        record = self.pause_controller.pause_until(
            _end_of_shift().astimezone(timezone.utc),
            "Paused until end of shift",
        )
        self._resume_warning_for = None
        self.wake_event.set()
        local_expiry = record.paused_until.astimezone()
        self._set_status("Paused", f"until {local_expiry:%H:%M}")
        self._notify(f"Face capture paused until end of shift at {local_expiry:%H:%M}.")
        return record

    def resume(self) -> None:
        self.pause_controller.clear()
        self._resume_warning_for = None
        self.wake_event.set()
        self._set_status("Active", "waiting for next sample")
        self._notify("Face capture resumed.")

    def stop(self) -> None:
        self.stop_event.set()
        self.wake_event.set()

    def _wait(self, seconds: float) -> None:
        self.wake_event.wait(timeout=max(0.0, seconds))
        self.wake_event.clear()

    def _handle_pause(self) -> bool:
        record = self.pause_controller.active()
        if not record:
            if self.status_text().startswith("Paused"):
                self._resume_warning_for = None
                self._notify("Pause expired. Face capture resumed automatically.")
            return False

        now = self.pause_controller.now()
        remaining = record.remaining_seconds(now)
        local_expiry = record.paused_until.astimezone()
        self._set_status("Paused", f"until {local_expiry:%H:%M}")

        if remaining <= RESUME_WARNING_SECONDS and self._resume_warning_for != record.paused_until:
            minutes = max(1, round(remaining / 60))
            self._notify(f"Face capture will resume automatically in about {minutes} minutes.")
            self._resume_warning_for = record.paused_until

        self._wait(min(1.0, remaining))
        return True

    def run(self) -> None:
        validate_config()
        next_capture_at = 0.0
        last_face_seen = 0.0
        current_session_id: str | None = None

        while not self.stop_event.is_set():
            if self._handle_pause():
                continue

            now = time.monotonic()
            if now < next_capture_at:
                self._set_status("Active", "camera released")
                self._wait(min(1.0, next_capture_at - now))
                continue

            self._set_status("Sampling", "camera in use briefly")
            frame = capture_frame()
            if frame is None:
                self._set_status(
                    "Camera busy",
                    f"retrying in {CAMERA_BUSY_RETRY_SECONDS:g} seconds",
                )
                next_capture_at = time.monotonic() + CAMERA_BUSY_RETRY_SECONDS
                continue

            # The camera is already released here. If a pause arrived during the
            # brief capture, discard this frame rather than processing it.
            if self.pause_controller.active():
                continue

            self._set_status("Active", "camera released")
            next_capture_at = time.monotonic() + CAPTURE_INTERVAL_SECONDS
            face = largest_face(frame)
            if face is None:
                session_expired = (
                    current_session_id
                    and time.monotonic() - last_face_seen > SESSION_RESET_SECONDS
                )
                if session_expired:
                    current_session_id = None
                continue

            last_face_seen = time.monotonic()
            if current_session_id is None:
                current_session_id = uuid.uuid4().hex

            encoded, jpeg = cv2.imencode(".jpg", face, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if not encoded:
                continue

            payload = jpeg.tobytes()
            try:
                flush_queue()
                if not upload_image(payload, current_session_id):
                    queue_locally(payload, current_session_id)
            except requests.RequestException:
                queue_locally(payload, current_session_id)


def _status_message(controller: PauseController) -> str:
    record = controller.active()
    if not record:
        return f"Capture is active. State file: {controller.state_file}"
    local_expiry = record.paused_until.astimezone()
    return (
        f"Capture is paused until {local_expiry:%Y-%m-%d %H:%M:%S %Z}. "
        f"Reason: {record.reason}. State file: {controller.state_file}"
    )


def run_with_tray(agent: DeviceAgent) -> None:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "System-tray support is not installed. Run 'python -m pip install -r "
            "requirements.txt' or start with --no-tray."
        ) from exc

    image = Image.new("RGBA", (64, 64), (18, 24, 38, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 56, 56), radius=14, fill=(109, 94, 252, 255))
    draw.rectangle((20, 20, 28, 44), fill="white")
    draw.rectangle((34, 20, 44, 30), fill="white")
    draw.rectangle((34, 34, 44, 44), fill="white")

    def pause_handler(minutes: int):
        return lambda _icon, _item: agent.pause_for(minutes)

    def pause_to_shift_end(_icon, _item):
        agent.pause_until_end_of_shift()

    def resume_handler(_icon, _item):
        agent.resume()

    def exit_handler(icon, _item):
        agent.stop()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(lambda _item: f"Status: {agent.status_text()}", None, enabled=False),
        pystray.MenuItem(
            "Pause capture",
            pystray.Menu(
                pystray.MenuItem("15 minutes", pause_handler(15)),
                pystray.MenuItem("30 minutes", pause_handler(30)),
                pystray.MenuItem("1 hour", pause_handler(60)),
                pystray.MenuItem("Until end of shift", pause_to_shift_end),
            ),
        ),
        pystray.MenuItem(
            "Resume now",
            resume_handler,
            enabled=lambda _item: agent.pause_controller.active() is not None,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit agent", exit_handler),
    )
    icon = pystray.Icon("sentiment-grid-camera", image, "Sentiment Grid Camera", menu)
    agent.set_notifier(lambda message: icon.notify(message, "Sentiment Grid Camera"))
    agent.set_status_listener(icon.update_menu)

    errors: list[BaseException] = []

    def agent_target() -> None:
        try:
            agent.run()
        except BaseException as exc:
            errors.append(exc)
            agent._set_status("Error", str(exc))
            agent._notify(f"Camera agent stopped: {exc}")

    thread = threading.Thread(target=agent_target, name="camera-capture", daemon=True)
    thread.start()
    try:
        icon.run()
    finally:
        agent.stop()
        thread.join(timeout=5)
    if errors:
        raise errors[0]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sentiment Grid background camera agent")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--pause", type=int, metavar="MINUTES", help="pause for a finite time")
    actions.add_argument(
        "--pause-until-shift-end",
        action="store_true",
        help="pause until SHIFT_END_HOUR",
    )
    actions.add_argument("--resume", action="store_true", help="resume capture now")
    actions.add_argument("--status", action="store_true", help="show current pause status")
    parser.add_argument("--reason", default="Administrator pause", help="reason for pausing")
    parser.add_argument("--no-tray", action="store_true", help="run without a system-tray icon")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_argument_parser().parse_args(argv)
    controller = PauseController()

    if args.pause is not None:
        record = controller.pause_for(timedelta(minutes=args.pause), args.reason)
        print(f"Capture paused until {record.paused_until.astimezone():%Y-%m-%d %H:%M:%S %Z}.")
        return
    if args.pause_until_shift_end:
        record = controller.pause_until(
            _end_of_shift().astimezone(timezone.utc),
            args.reason or "Paused until end of shift",
        )
        print(f"Capture paused until {record.paused_until.astimezone():%Y-%m-%d %H:%M:%S %Z}.")
        return
    if args.resume:
        controller.clear()
        print("Capture resumed.")
        return
    if args.status:
        print(_status_message(controller))
        return

    validate_config()
    agent = DeviceAgent(controller)
    try:
        if args.no_tray:
            agent.run()
        else:
            run_with_tray(agent)
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
