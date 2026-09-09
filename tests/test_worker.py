import sys
import tempfile
import types
import unittest
from datetime import datetime
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


def worker_settings(**overrides):
    values = {
        "enable_face_identification": False,
        "embedding_model": "ArcFace",
        "delete_raw_image_after_processing": True,
        "emotion_detector_backend": "retinaface",
        "emotion_expand_percentage": 10,
        "emotion_smoothing_frames": 3,
        "emotion_smoothing_window_seconds": 4.0,
        "emotion_min_samples": 1,
        "emotion_min_confidence": 0.55,
        "emotion_min_margin": 0.10,
        "emotion_min_face_size": 80,
        "emotion_min_sharpness": 0.0,
        "emotion_min_brightness": 0.0,
        "emotion_max_brightness": 255.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class WorkerTests(unittest.TestCase):
    def test_warm_models_loads_emotion_as_a_facial_attribute(self):
        deepface = Mock()

        with (
            patch.object(worker, "get_deepface", return_value=deepface),
            patch.object(
                worker,
                "settings",
                worker_settings(
                    enable_face_identification=True,
                ),
            ),
        ):
            worker.warm_models()

        self.assertEqual(
            deepface.build_model.call_args_list,
            [
                call("Emotion", task="facial_attribute"),
                call("retinaface", task="face_detector"),
                call("ArcFace"),
            ],
        )

    def test_three_frame_consensus_outvotes_one_sad_result(self):
        vectors = [
            {"happy": 0.80, "sad": 0.20},
            {"happy": 0.75, "sad": 0.25},
            {"happy": 0.20, "sad": 0.80},
        ]

        with patch.object(
            worker,
            "settings",
            worker_settings(emotion_min_samples=2),
        ):
            combined = worker._average_vectors(vectors)
            emotion, confidence = worker._classify_emotion(combined, sample_count=3)

        self.assertEqual(emotion, "happy")
        self.assertAlmostEqual(confidence, 0.5833333333)

    def test_close_probabilities_are_reported_as_uncertain(self):
        with patch.object(
            worker,
            "settings",
            worker_settings(emotion_min_samples=2),
        ):
            emotion, confidence = worker._classify_emotion(
                {"happy": 0.52, "sad": 0.48},
                sample_count=3,
            )

        self.assertEqual(emotion, "uncertain")
        self.assertAlmostEqual(confidence, 0.52)

    def test_blurry_image_is_rejected_before_inference(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        with (
            patch.object(
                worker,
                "settings",
                worker_settings(emotion_min_sharpness=25.0),
            ),
            self.assertRaises(worker.PoorImageQualityError),
        ):
            worker._validate_image_quality(frame)

    def test_rejected_image_is_deleted_when_raw_retention_is_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blurry-face.jpg"
            cv2.imwrite(str(path), np.zeros((100, 100, 3), dtype=np.uint8))
            snapshot = {
                "id": 10,
                "job_id": "01TESTJOB",
                "device_id": 3,
                "session_id": "visit12345",
                "image_path": str(path),
                "timestamp": datetime(2026, 9, 9, 13, 0),
            }

            with (
                patch.object(
                    worker,
                    "settings",
                    worker_settings(emotion_min_sharpness=25.0),
                ),
                patch.object(worker, "get_snapshot", return_value=snapshot),
                patch.object(worker, "mark_processing"),
                patch.object(worker, "mark_failed") as mark_failed,
            ):
                result = worker.process_snapshot(10)

            self.assertEqual(result["status"], "rejected")
            mark_failed.assert_called_once_with(10, "PoorImageQuality")
            self.assertFalse(path.exists())

    def test_processing_applies_burst_consensus_to_recent_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "face.jpg"
            cv2.imwrite(str(path), np.zeros((100, 100, 3), dtype=np.uint8))
            snapshot = {
                "id": 10,
                "job_id": "01TESTJOB",
                "device_id": 3,
                "session_id": "visit12345",
                "image_path": str(path),
                "timestamp": datetime(2026, 9, 9, 13, 0),
            }
            deepface = Mock()
            deepface.analyze.return_value = {
                "dominant_emotion": "happy",
                "emotion": {"happy": 92.0, "neutral": 8.0},
            }

            with (
                patch.object(
                    worker,
                    "settings",
                    worker_settings(
                        delete_raw_image_after_processing=False,
                        emotion_min_samples=2,
                    ),
                ),
                patch.object(worker, "get_deepface", return_value=deepface),
                patch.object(worker, "get_snapshot", return_value=snapshot),
                patch.object(
                    worker,
                    "get_recent_session_emotions",
                    return_value=[(9, {"happy": 0.70, "neutral": 0.30})],
                ),
                patch.object(worker, "mark_processing"),
                patch.object(worker, "create_visitor", return_value=55),
                patch.object(worker, "complete_snapshot") as complete_snapshot,
                patch.object(worker, "mark_failed") as mark_failed,
            ):
                result = worker.process_snapshot(10)

            self.assertEqual(result["emotion"], "happy")
            kwargs = complete_snapshot.call_args.kwargs
            self.assertEqual(kwargs["consensus_snapshot_ids"], [9])
            self.assertAlmostEqual(kwargs["confidence"], 0.81)
            deepface.analyze.assert_called_once()
            analyze_kwargs = deepface.analyze.call_args.kwargs
            self.assertEqual(analyze_kwargs["detector_backend"], "retinaface")
            self.assertTrue(analyze_kwargs["align"])
            mark_failed.assert_not_called()

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
                "timestamp": datetime(2026, 9, 9, 13, 0),
            }
            deepface_module = types.ModuleType("deepface")
            deepface_module.DeepFace = FakeDeepFace

            with (
                patch.dict(sys.modules, {"deepface": deepface_module}),
                patch.object(
                    worker,
                    "settings",
                    worker_settings(),
                ),
                patch.object(worker, "get_snapshot", return_value=snapshot),
                patch.object(
                    worker,
                    "get_recent_session_emotions",
                    return_value=[],
                ),
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
            self.assertEqual(kwargs["consensus_snapshot_ids"], [])
            self.assertIsNone(kwargs["image_path"])
            mark_failed.assert_not_called()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
