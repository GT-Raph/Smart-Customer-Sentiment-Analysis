import unittest
from unittest.mock import Mock, patch

from clients import device_agent


class DeviceAgentResponseTests(unittest.TestCase):
    @patch.object(device_agent.requests, "post")
    def test_permanent_and_retryable_responses_are_classified(self, post):
        for status_code, expected in (
            (201, "success"),
            (400, "reject"),
            (403, "reject"),
            (408, "retry"),
            (415, "reject"),
            (422, "reject"),
            (429, "retry"),
            (500, "retry"),
            (503, "retry"),
        ):
            with self.subTest(status_code=status_code):
                post.return_value = Mock(status_code=status_code)
                self.assertEqual(
                    device_agent.upload_image(b"jpeg", "session"),
                    expected,
                )

    @patch.object(device_agent.requests, "post")
    def test_unauthorized_response_stops_for_bad_credentials(self, post):
        post.return_value = Mock(status_code=401)

        with self.assertRaisesRegex(RuntimeError, "credentials"):
            device_agent.upload_image(b"jpeg", "session")


if __name__ == "__main__":
    unittest.main()
