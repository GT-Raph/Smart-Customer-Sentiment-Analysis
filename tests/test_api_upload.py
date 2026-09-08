import io
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile

from api_server import face_api


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeDatabase:
    def cursor(self, **kwargs):
        return FakeCursor()


@contextmanager
def fake_database():
    yield FakeDatabase()


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.bank = {"id": 2, "code": "BANK_A", "name": "Bank A"}
        self.branch = {
            "id": 3,
            "code": "MAIN",
            "name": "Main",
            "matched_prefix": "PC-",
        }
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def jpeg_bytes():
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        assert ok
        return encoded.tobytes()

    @staticmethod
    def upload(content, content_type="image/jpeg"):
        return UploadFile(
            filename="face.jpg",
            file=io.BytesIO(content),
            headers={"content-type": content_type},
        )

    def test_valid_image_is_processed_for_the_matched_branch(self):
        with (
            patch.object(face_api, "CAPTURED_FACES_ROOT", Path(self.temp.name)),
            patch.object(face_api, "get_db", fake_database),
            patch.object(face_api, "get_branch_by_pc_name", return_value=self.branch),
            patch.object(
                face_api,
                "process_face_image",
                return_value=[{"face_id": "visitor-1", "emotion": "happy", "confidence": 90.0}],
            ),
        ):
            result = face_api.upload_face(
                self.upload(self.jpeg_bytes()),
                pc_name="pc-001",
                bank=self.bank,
            )

        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["branch"]["code"], "MAIN")
        self.assertEqual(result["pc_name"], "PC-001")
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.jpg"))), 1)

    def test_unmatched_computer_is_rejected(self):
        with (
            patch.object(face_api, "get_db", fake_database),
            patch.object(face_api, "get_branch_by_pc_name", return_value=None),
        ):
            with self.assertRaises(HTTPException) as raised:
                face_api.upload_face(
                    self.upload(self.jpeg_bytes()),
                    pc_name="unknown-pc",
                    bank=self.bank,
                )
        self.assertEqual(raised.exception.status_code, 403)

    def test_unsupported_content_type_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            face_api.upload_face(
                self.upload(b"not-an-image", "text/plain"),
                pc_name="pc-001",
                bank=self.bank,
            )
        self.assertEqual(raised.exception.status_code, 415)

    def test_invalid_image_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            face_api.upload_face(
                self.upload(b"not-an-image"),
                pc_name="pc-001",
                bank=self.bank,
            )
        self.assertEqual(raised.exception.status_code, 400)

    def test_failed_processing_removes_stored_image(self):
        with (
            patch.object(face_api, "CAPTURED_FACES_ROOT", Path(self.temp.name)),
            patch.object(face_api, "get_db", fake_database),
            patch.object(face_api, "get_branch_by_pc_name", return_value=self.branch),
            patch.object(face_api, "process_face_image", side_effect=ValueError("No face")),
        ):
            with self.assertRaises(HTTPException) as raised:
                face_api.upload_face(
                    self.upload(self.jpeg_bytes()),
                    pc_name="pc-001",
                    bank=self.bank,
                )
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(list(Path(self.temp.name).rglob("*.jpg")), [])


if __name__ == "__main__":
    unittest.main()
