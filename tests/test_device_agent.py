import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np

from clients import device_agent


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class FakeCamera:
    def __init__(self, opened: bool, frames: list[tuple[bool, object]]) -> None:
        self.opened = opened
        self.frames = iter(frames)
        self.released = False

    def isOpened(self) -> bool:
        return self.opened

    def read(self):
        return next(self.frames, (False, None))

    def release(self) -> None:
        self.released = True


class PauseControllerTests(unittest.TestCase):
    def test_pause_persists_and_expires_automatically(self):
        start = datetime(2026, 9, 9, 9, 0, tzinfo=timezone.utc)
        clock = MutableClock(start)
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"
            controller = device_agent.PauseController(state_file, now=clock)

            controller.pause_for(timedelta(minutes=30), "Video call")

            active = controller.active()
            self.assertIsNotNone(active)
            self.assertEqual(active.reason, "Video call")
            self.assertTrue(state_file.exists())

            clock.value = start + timedelta(minutes=31)
            self.assertIsNone(controller.active())
            self.assertFalse(state_file.exists())

    def test_pause_survives_a_new_controller_instance(self):
        start = datetime(2026, 9, 9, 9, 0, tzinfo=timezone.utc)
        clock = MutableClock(start)
        with tempfile.TemporaryDirectory() as directory:
            state_file = Path(directory) / "state.json"
            device_agent.PauseController(state_file, now=clock).pause_for(
                timedelta(minutes=15),
                "Teller pause",
            )

            restored = device_agent.PauseController(state_file, now=clock).active()

            self.assertIsNotNone(restored)
            self.assertEqual(restored.paused_until, start + timedelta(minutes=15))


class CameraReleaseTests(unittest.TestCase):
    def test_burst_captures_multiple_images_before_releasing_camera(self):
        frames = [np.full((10, 10, 3), value, dtype=np.uint8) for value in range(3)]
        camera = FakeCamera(True, [(True, frame) for frame in frames])

        with patch.object(device_agent.cv2, "VideoCapture", return_value=camera):
            result = device_agent.capture_frames(
                warmup_frames=1,
                warmup_delay_seconds=0,
                active_seconds=1,
                max_images=3,
                image_interval_seconds=0,
            )

        self.assertEqual(len(result), 3)
        self.assertIs(result[0], frames[0])
        self.assertIs(result[2], frames[2])
        self.assertTrue(camera.released)

    def test_camera_is_released_after_a_successful_capture(self):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        camera = FakeCamera(True, [(True, frame)])

        with patch.object(device_agent.cv2, "VideoCapture", return_value=camera):
            result = device_agent.capture_frame(warmup_frames=1, warmup_delay_seconds=0)

        self.assertIs(result, frame)
        self.assertTrue(camera.released)

    def test_unavailable_camera_is_released_before_retry(self):
        camera = FakeCamera(False, [])

        with patch.object(device_agent.cv2, "VideoCapture", return_value=camera):
            result = device_agent.capture_frames(
                warmup_frames=1,
                warmup_delay_seconds=0,
                active_seconds=1,
                max_images=3,
                image_interval_seconds=0,
            )

        self.assertEqual(result, [])
        self.assertTrue(camera.released)


if __name__ == "__main__":
    unittest.main()
