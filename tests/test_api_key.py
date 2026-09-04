import unittest

from api_server.security import api_key_prefix, hash_api_key


class ApiKeyTests(unittest.TestCase):
    def test_extracts_valid_prefix(self):
        self.assertEqual(api_key_prefix("scs_abc123_secret"), "abc123")

    def test_rejects_malformed_key(self):
        self.assertIsNone(api_key_prefix("not-a-device-key"))

    def test_hash_is_stable_and_not_plaintext(self):
        token = "scs_abc123_secret"
        digest = hash_api_key(token)
        self.assertEqual(digest, hash_api_key(token))
        self.assertNotIn(token, digest)
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
