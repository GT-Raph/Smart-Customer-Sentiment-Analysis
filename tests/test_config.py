import unittest

from api_server.config import Settings, database_url_from_environment


class DatabaseConfigurationTests(unittest.TestCase):
    def test_supabase_url_takes_precedence_over_legacy_database_url(self):
        value = database_url_from_environment(
            {
                "SUPABASE_DB_URL": "postgresql://user:pass@pooler.supabase.com:5432/postgres",
                "DATABASE_URL": "postgresql://legacy:pass@localhost:5432/legacy",
            }
        )
        self.assertIn("pooler.supabase.com", value)
        self.assertTrue(value.endswith("?sslmode=require"))

    def test_separate_values_url_encode_password(self):
        value = database_url_from_environment(
            {
                "SUPABASE_DB_NAME": "postgres",
                "SUPABASE_DB_USER": "postgres.project",
                "SUPABASE_DB_PASSWORD": "p@ss:#/%word",
                "SUPABASE_DB_HOST": "aws-0-region.pooler.supabase.com",
                "SUPABASE_DB_PORT": "5432",
            }
        )
        self.assertIn("p%40ss%3A%23%2F%25word", value)
        self.assertTrue(value.endswith("?sslmode=require"))

    def test_short_db_names_are_supported(self):
        value = database_url_from_environment(
            {
                "DB_ENGINE": "postgresql",
                "DB_NAME": "postgres",
                "DB_USER": "postgres.project",
                "DB_PASSWORD": "p@ss:#/%word",
                "DB_HOST": "aws-0-region.pooler.supabase.com",
                "DB_PORT": "5432",
                "DB_SSLMODE": "require",
            }
        )
        self.assertIn("p%40ss%3A%23%2F%25word", value)
        self.assertTrue(value.endswith("?sslmode=require"))

    def test_separate_values_preserve_configured_sslmode(self):
        value = database_url_from_environment(
            {
                "DB_ENGINE": "postgresql",
                "DB_NAME": "postgres",
                "DB_USER": "postgres.project",
                "DB_PASSWORD": "password",
                "DB_HOST": "pooler.supabase.com",
                "DB_PORT": "5432",
                "DB_SSLMODE": "verify-full",
            }
        )
        self.assertTrue(value.endswith("?sslmode=verify-full"))

    def test_incomplete_separate_values_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, r"\bDB_PASSWORD\b"):
            database_url_from_environment(
                {
                    "SUPABASE_DB_NAME": "postgres",
                    "SUPABASE_DB_USER": "postgres.project",
                }
            )

    def test_ingestion_api_rejects_non_postgresql_url(self):
        with self.assertRaisesRegex(RuntimeError, "requires a PostgreSQL"):
            Settings(database_url="sqlite:///local.sqlite3").validate()


if __name__ == "__main__":
    unittest.main()
