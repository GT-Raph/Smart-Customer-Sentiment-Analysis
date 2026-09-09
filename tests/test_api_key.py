import hashlib
import unittest

from api_server.config import MAX_EMBEDDING_CANDIDATES
from api_server.db_utils import (
    get_branch_by_pc_name,
    get_embeddings_db,
    verify_bank_api_key,
)


class FakeCursor:
    def __init__(self, *, one=None, many=None):
        self.one = one
        self.many = many or []
        self.executions = []

    def execute(self, query, params):
        self.executions.append((query, params))

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class BankAuthenticationTests(unittest.TestCase):
    def test_valid_bank_key_is_accepted(self):
        token = "a-secure-bank-api-key-value"
        bank = {
            "id": 4,
            "code": "BANK_A",
            "name": "Bank A",
            "api_key_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        }
        result = verify_bank_api_key(
            FakeCursor(one=bank),
            "bank_a",
            token,
        )
        self.assertEqual(result, bank)

    def test_invalid_bank_key_is_rejected(self):
        bank = {
            "id": 4,
            "code": "BANK_A",
            "name": "Bank A",
            "api_key_hash": hashlib.sha256(b"correct-token").hexdigest(),
        }
        result = verify_bank_api_key(
            FakeCursor(one=bank),
            "BANK_A",
            "wrong-token",
        )
        self.assertIsNone(result)

    def test_unknown_bank_is_rejected(self):
        result = verify_bank_api_key(
            FakeCursor(one=None),
            "UNKNOWN",
            "any-key",
        )
        self.assertIsNone(result)

    def test_bank_without_api_key_hash_is_rejected(self):
        bank = {
            "id": 4,
            "code": "BANK_A",
            "name": "Bank A",
            "api_key_hash": "",
        }
        result = verify_bank_api_key(
            FakeCursor(one=bank),
            "BANK_A",
            "supplied-key",
        )
        self.assertIsNone(result)

    def test_longest_matching_branch_prefix_wins(self):
        cursor = FakeCursor(
            many=[
                {"id": 1, "bank_id": 4, "code": "A", "name": "A", "pc_prefix": "PC", "location": ""},
                {"id": 2, "bank_id": 4, "code": "B", "name": "B", "pc_prefix": "PC-ACCRA", "location": ""},
            ]
        )
        branch = get_branch_by_pc_name(cursor, 4, "pc-accra-01")
        self.assertEqual(branch["id"], 2)
        self.assertEqual(branch["matched_prefix"], "PC-ACCRA")

    def test_embedding_candidates_are_retention_scoped_and_bounded(self):
        cursor = FakeCursor(many=[])

        self.assertEqual(get_embeddings_db(cursor, 4), [])

        query, params = cursor.executions[0]
        normalized_query = " ".join(query.split())
        self.assertIn("tenant_bank_settings", normalized_query)
        self.assertIn("record_retention_days", normalized_query)
        self.assertIn("ORDER BY candidate.last_seen DESC", normalized_query)
        self.assertIn("LIMIT %s", normalized_query)
        self.assertEqual(params, (4, 4, MAX_EMBEDDING_CANDIDATES))


if __name__ == "__main__":
    unittest.main()
