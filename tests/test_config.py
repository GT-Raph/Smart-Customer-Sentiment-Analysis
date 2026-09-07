import os
import unittest
from unittest.mock import patch

from api_server.config import mysql_options_from_env


class DatabaseConfigurationTests(unittest.TestCase):
    def test_xampp_mysql_settings_preserve_reserved_password_characters(self):
        password = "p@ss:Z9/?#"
        with patch.dict(
            os.environ,
            {
                "MYSQL_DATABASE": "smart_sentiment",
                "MYSQL_USER": "sentiment_app",
                "MYSQL_PASSWORD": password,
                "MYSQL_HOST": "127.0.0.1",
                "MYSQL_PORT": "3306",
            },
            clear=True,
        ):
            options = mysql_options_from_env()

        self.assertEqual(options["host"], "127.0.0.1")
        self.assertEqual(options["port"], 3306)
        self.assertEqual(options["db"], "smart_sentiment")
        self.assertEqual(options["user"], "sentiment_app")
        self.assertEqual(options["passwd"], password)

    def test_invalid_mysql_port_is_rejected(self):
        with patch.dict(os.environ, {"MYSQL_PORT": "not-a-port"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "MYSQL_PORT"):
                mysql_options_from_env()

    def test_defaults_match_local_xampp(self):
        with patch.dict(os.environ, {}, clear=True):
            options = mysql_options_from_env()

        self.assertEqual(options["host"], "127.0.0.1")
        self.assertEqual(options["port"], 3306)
        self.assertEqual(options["db"], "smart_sentiment")
        self.assertEqual(options["user"], "root")
        self.assertEqual(options["passwd"], "")


if __name__ == "__main__":
    unittest.main()
