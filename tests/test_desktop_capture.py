import unittest
from unittest.mock import Mock, patch

import numpy as np
import requests

import desktop_capture


class CaptureHelperTests(unittest.TestCase):
    def test_iou_handles_overlap_and_disjoint_boxes(self):
        self.assertAlmostEqual(
            desktop_capture.iou(
                (0, 0, 10, 10),
                (5, 5, 10, 10),
            ),
            25 / 175,
        )
        self.assertEqual(
            desktop_capture.iou(
                (0, 0, 10, 10),
                (20, 20, 5, 5),
            ),
            0.0,
        )

    def test_get_roi_converts_fractional_bounds_to_pixels(self):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        with (
            patch.object(desktop_capture, "ROI_LEFT", 0.10),
            patch.object(desktop_capture, "ROI_TOP", 0.20),
            patch.object(desktop_capture, "ROI_RIGHT", 0.90),
            patch.object(desktop_capture, "ROI_BOTTOM", 0.80),
        ):
            self.assertEqual(
                desktop_capture.get_roi(frame),
                (20, 20, 160, 60),
            )

    def test_safe_component_replaces_path_punctuation(self):
        self.assertEqual(
            desktop_capture.safe_component("BANK A/PC:01"),
            "BANK_A_PC_01",
        )

    @patch.object(desktop_capture.requests, "post")
    def test_send_to_api_classifies_response_statuses(self, post):
        for status_code, expected in (
            (201, "success"),
            (400, "reject"),
            (401, "reject"),
            (403, "reject"),
            (415, "reject"),
            (422, "reject"),
            (408, "retry"),
            (429, "retry"),
            (500, "retry"),
            (503, "retry"),
        ):
            with self.subTest(status_code=status_code):
                response = Mock()
                response.status_code = status_code
                response.text = "response detail"
                response.json.return_value = {
                    "detail": "response detail"
                }
                post.return_value = response

                result, _, _ = desktop_capture.send_to_api(
                    b"jpeg",
                    "capture.jpg",
                )
                self.assertEqual(result, expected)

    @patch.object(
        desktop_capture.requests,
        "post",
        side_effect=requests.ConnectionError("offline"),
    )
    def test_send_to_api_retries_connection_errors(self, _post):
        result, _, payload = desktop_capture.send_to_api(
            b"jpeg",
            "capture.jpg",
        )
        self.assertEqual(result, "retry")
        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
