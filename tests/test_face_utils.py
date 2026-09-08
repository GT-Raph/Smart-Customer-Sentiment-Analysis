import unittest

import numpy as np

from api_server.face_utils import match_face_id


class MatchFaceTests(unittest.TestCase):
    def test_returns_nearest_match_not_first_match(self):
        known = [
            ("far", np.array([1.0, 0.0, 0.0])),
            ("near", np.array([0.0, 1.0, 0.0])),
        ]
        result = match_face_id(
            np.array([0.0, 0.99, 0.01]),
            known,
            threshold=0.2,
        )
        self.assertEqual(result, "near")

    def test_returns_none_when_threshold_not_met(self):
        known = [("a", np.array([1.0, 0.0]))]
        self.assertIsNone(
            match_face_id(
                np.array([0.0, 1.0]),
                known,
                threshold=0.2,
            )
        )


if __name__ == "__main__":
    unittest.main()
