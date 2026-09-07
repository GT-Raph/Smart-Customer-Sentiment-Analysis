import os
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from api_server.config import database_url_from_env


class DatabaseConfigurationTests(unittest.TestCase):
    def test_discrete_postgres_settings_escape_reserved_password_characters(self):
        password = "p@ss:Z9/?#"
        with patch.dict(
            os.environ,
            {
                "POSTGRES_DB": "sentiment",
                "POSTGRES_USER": "sentiment",
                "POSTGRES_PASSWORD": password,
                "POSTGRES_HOST": "localhost",
                "POSTGRES_PORT": "5432",
            },
            clear=True,
        ):
            parsed = urlparse(database_url_from_env())

        self.assertEqual(parsed.hostname, "localhost")
        self.assertEqual(parsed.port, 5432)
        self.assertEqual(unquote(parsed.password or ""), password)

    def test_database_url_remains_available_as_an_alternative(self):
        expected = "postgresql://user:password@database.example:5432/app"
        with patch.dict(os.environ, {"DATABASE_URL": expected}, clear=True):
            self.assertEqual(database_url_from_env(), expected)


if __name__ == "__main__":
    unittest.main()
