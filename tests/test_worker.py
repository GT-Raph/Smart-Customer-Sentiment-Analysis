import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import cv2
import numpy as np

from api_server import worker


class FakeDeepFace:
    @staticmethod
    def analyze(**kwargs):
        return {
            "dominant_emotion": "happy",
            "emotion": {"happy": 92.0, "neutral": 8.0},
        }


class WorkerTests(unittest.TestCase):
    def test_warm_models_loads_emotion_as_a_facial_attribute(self):
        deepface = Mock()

        with (
            patch.object(worker, "get_deepface", return_value=deepface),
            patch.object(
                worker,
                "settings",
                SimpleNamespace(
                    enable_face_identification=True,
                    embedding_model="ArcFace",
                ),
            ),
        ):
            worker.warm_models()

        self.assertEqual(
            deepface.build_model.call_args_list,
            [call("Emotion", task="facial_attribute"), call("ArcFace")],
        )

    def test_anonymous_processing_updates_snapshot_and_deletes_raw_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "face.jpg"
            cv2.imwrite(str(path), np.zeros((100, 100, 3), dtype=np.uint8))
            snapshot = {
                "id": 10,
                "job_id": "01TESTJOB",
                "device_id": 3,
                "session_id": "visit12345",
                "image_path": str(path),
            }
            deepface_module = types.ModuleType("deepface")
            deepface_module.DeepFace = FakeDeepFace

            with (
                patch.dict(sys.modules, {"deepface": deepface_module}),
                patch.object(
                    worker,
                    "settings",
                    SimpleNamespace(
                        enable_face_identification=False,
                        delete_raw_image_after_processing=True,
                    ),
                ),
                patch.object(worker, "get_snapshot", return_value=snapshot),
                patch.object(worker, "mark_processing") as mark_processing,
                patch.object(worker, "create_visitor", return_value=55) as create_visitor,
                patch.object(worker, "complete_snapshot") as complete_snapshot,
                patch.object(worker, "mark_failed") as mark_failed,
            ):
                result = worker.process_snapshot(10)

            self.assertEqual(result["emotion"], "happy")
            mark_processing.assert_called_once_with(10)
            create_visitor.assert_called_once_with("session-3-visit12345")
            complete_snapshot.assert_called_once()
            kwargs = complete_snapshot.call_args.kwargs
            self.assertAlmostEqual(kwargs["confidence"], 0.92)
            self.assertIsNone(kwargs["image_path"])
            mark_failed.assert_not_called()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
