import hashlib
import unittest

from api_server.db_utils import get_branch_by_pc_name, verify_bank_api_key


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


if __name__ == "__main__":
    unittest.main()
