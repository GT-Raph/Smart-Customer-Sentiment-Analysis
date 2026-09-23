import unittest
from types import SimpleNamespace
from unittest.mock import patch

from rq.worker import WorkerStatus

from scripts.check_pipeline import _api_health_url, _worker_is_active


class PipelineStatusTests(unittest.TestCase):
    def test_health_url_uses_ingestion_service_origin(self):
        with patch.dict(
            "os.environ",
            {"INGESTION_API_URL": "https://camera.example.test/v1/snapshots"},
        ):
            self.assertEqual(
                _api_health_url(),
                "https://camera.example.test/health",
            )

    def test_rq_enum_idle_worker_is_active(self):
        self.assertTrue(_worker_is_active(SimpleNamespace(state=WorkerStatus.IDLE)))

    def test_stopped_worker_is_not_active(self):
        self.assertFalse(_worker_is_active(SimpleNamespace(state="stopped")))


if __name__ == "__main__":
    unittest.main()
