import asyncio
import io
import tempfile
import unittest
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
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self, **kwargs):
        return FakeCursor()


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.bank = {"id": 2, "code": "BANK_A", "name": "Bank A"}
        self.branch = {
            "id": 3,
            "code": "MAIN",
            "name": "Main",
            "matched_prefix": "PC-",
        }
        self.database = FakeDatabase()
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

    def run_upload(self, content, *, pc_name="pc-001", content_type="image/jpeg"):
        return asyncio.run(
            face_api.upload_face(
                self.upload(content, content_type),
                pc_name=pc_name,
                bank=self.bank,
            )
        )

    def test_valid_image_is_processed_for_the_matched_branch(self):
        with (
            patch.object(
                face_api,
                "captured_faces_root",
                return_value=Path(self.temp.name),
            ),
            patch.object(
                face_api,
                "get_branch_by_pc_name",
                return_value=self.branch,
            ) as branch_lookup,
            patch.object(
                face_api,
                "get_db",
                return_value=self.database,
            ),
            patch.object(
                face_api,
                "process_face_image",
                return_value=[{"face_id": "visitor-1", "emotion": "happy", "confidence": 90.0}],
            ) as process_image,
        ):
            result = self.run_upload(self.jpeg_bytes())

        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["branch"]["code"], "MAIN")
        self.assertEqual(result["pc_name"], "PC-001")
        self.assertEqual(len(list(Path(self.temp.name).rglob("*.jpg"))), 1)
        self.assertEqual(
            branch_lookup.call_args.args[1:],
            (self.bank["id"], "PC-001"),
        )
        self.assertIs(
            process_image.call_args.kwargs["database"],
            self.database,
        )

    def test_busy_processor_returns_503_and_removes_stored_image(self):
        class BusyCapacity:
            async def acquire(self):
                await asyncio.sleep(1)

            def release(self):
                raise AssertionError("unacquired capacity must not be released")

        with (
            patch.object(
                face_api,
                "captured_faces_root",
                return_value=Path(self.temp.name),
            ),
            patch.object(
                face_api,
                "get_branch_by_pc_name",
                return_value=self.branch,
            ),
            patch.object(face_api, "get_db", return_value=self.database),
            patch.object(face_api, "FACE_PROCESSING_CAPACITY", BusyCapacity()),
            patch.object(face_api, "FACE_PROCESSING_CAPACITY_WAIT_SECONDS", 0.001),
        ):
            with self.assertRaises(HTTPException) as raised:
                self.run_upload(self.jpeg_bytes())

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(list(Path(self.temp.name).rglob("*.jpg")), [])

    def test_unmatched_computer_is_rejected(self):
        with (
            patch.object(face_api, "get_branch_by_pc_name", return_value=None),
            patch.object(face_api, "get_db", return_value=self.database),
        ):
            with self.assertRaises(HTTPException) as raised:
                self.run_upload(
                    self.jpeg_bytes(),
                    pc_name="unknown-pc",
                )
        self.assertEqual(raised.exception.status_code, 403)

    def test_unsupported_content_type_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            self.run_upload(
                b"not-an-image",
                content_type="text/plain",
            )
        self.assertEqual(raised.exception.status_code, 415)

    def test_invalid_image_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            self.run_upload(b"not-an-image")
        self.assertEqual(raised.exception.status_code, 400)

    def test_failed_processing_removes_stored_image(self):
        with (
            patch.object(
                face_api,
                "captured_faces_root",
                return_value=Path(self.temp.name),
            ),
            patch.object(face_api, "get_branch_by_pc_name", return_value=self.branch),
            patch.object(face_api, "get_db", return_value=self.database),
            patch.object(face_api, "process_face_image", side_effect=ValueError("No face")),
        ):
            with self.assertRaises(HTTPException) as raised:
                self.run_upload(self.jpeg_bytes())
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(list(Path(self.temp.name).rglob("*.jpg")), [])


if __name__ == "__main__":
    unittest.main()
