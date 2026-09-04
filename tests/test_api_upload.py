import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile

from api_server import face_api
from api_server.db_utils import DeviceContext, QuotaExceeded


class FakeQueue:
    def __init__(self):
        self.calls = []

    def enqueue(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.device = DeviceContext(
            id=1,
            organization_id=2,
            branch_id=3,
            name="front desk",
            pc_name="ACC001-CAM",
        )
        self.temp = tempfile.TemporaryDirectory()
        self.settings = SimpleNamespace(
            captured_faces_dir=Path(self.temp.name),
            max_upload_bytes=1024 * 1024,
            max_image_pixels=1_000_000,
            job_timeout_seconds=60,
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def jpeg_bytes() -> bytes:
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        return encoded.tobytes()

    def run_upload(self, content: bytes, content_type: str):
        upload = UploadFile(
            filename="face.jpg",
            file=io.BytesIO(content),
            headers={"content-type": content_type},
        )
        queue = FakeQueue()
        with (
            patch.object(face_api, "settings", self.settings),
            patch.object(face_api, "_rate_limit"),
            patch.object(face_api, "insert_snapshot", return_value=99),
            patch.object(face_api, "job_queue", return_value=queue),
        ):
            result = asyncio.run(face_api.upload_face(upload, session_id="session123", device=self.device))
        return result, queue

    def test_valid_image_is_queued(self):
        result, queue = self.run_upload(self.jpeg_bytes(), "image/jpeg")
        self.assertEqual(result["status"], "queued")
        self.assertEqual(len(queue.calls), 1)
        self.assertEqual(queue.calls[0][0][0], "api_server.worker.process_snapshot")
        self.assertEqual(queue.calls[0][0][1], 99)
        self.assertEqual(len(list(Path(self.temp.name).glob("*.jpg"))), 1)


    def test_monthly_quota_is_enforced_and_file_is_removed(self):
        upload = UploadFile(
            filename="face.jpg",
            file=io.BytesIO(self.jpeg_bytes()),
            headers={"content-type": "image/jpeg"},
        )
        with (
            patch.object(face_api, "settings", self.settings),
            patch.object(face_api, "_rate_limit"),
            patch.object(face_api, "insert_snapshot", side_effect=QuotaExceeded("Monthly analysis quota exceeded")),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    face_api.upload_face(
                        upload, session_id="session123", device=self.device
                    )
                )
        self.assertEqual(context.exception.status_code, 429)
        self.assertEqual(list(Path(self.temp.name).glob("*.jpg")), [])

    def test_invalid_session_id_is_rejected(self):
        upload = UploadFile(
            filename="face.jpg",
            file=io.BytesIO(self.jpeg_bytes()),
            headers={"content-type": "image/jpeg"},
        )
        with (
            patch.object(face_api, "settings", self.settings),
            patch.object(face_api, "_rate_limit"),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    face_api.upload_face(upload, session_id="bad id", device=self.device)
                )
        self.assertEqual(context.exception.status_code, 400)

    def test_unsupported_content_type_is_rejected(self):
        upload = UploadFile(
            filename="face.txt",
            file=io.BytesIO(b"not an image"),
            headers={"content-type": "text/plain"},
        )
        with patch.object(face_api, "_rate_limit"):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(face_api.upload_face(upload, session_id="session123", device=self.device))
        self.assertEqual(context.exception.status_code, 415)

    def test_invalid_image_is_rejected(self):
        upload = UploadFile(
            filename="face.jpg",
            file=io.BytesIO(b"not an image"),
            headers={"content-type": "image/jpeg"},
        )
        with (
            patch.object(face_api, "settings", self.settings),
            patch.object(face_api, "_rate_limit"),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(face_api.upload_face(upload, session_id="session123", device=self.device))
        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
