"""Read-only health check for the supported local service pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import MySQLdb
from redis import Redis
from rq import Queue, Worker

from api_server.config import settings


def _http_status(url: str) -> tuple[bool, str]:
    try:
        with urlopen(url, timeout=3) as response:
            status = int(response.status)
        return status < 500, f"HTTP {status}"
    except HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (OSError, URLError) as exc:
        return False, exc.__class__.__name__


def _api_health_url() -> str:
    upload_url = os.getenv(
        "INGESTION_API_URL",
        "http://127.0.0.1:8001/v1/snapshots",
    )
    parsed = urlsplit(upload_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "/health", "", ""))


def _worker_is_active(worker: object) -> bool:
    state = getattr(worker, "state", "")
    value = getattr(state, "value", state)
    return str(value).lower() in {"busy", "idle", "started"}


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    try:
        connection = MySQLdb.connect(**settings.mysql_options)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        finally:
            connection.close()
        results.append(("XAMPP database", True, "reachable"))
    except Exception as exc:
        results.append(("XAMPP database", False, exc.__class__.__name__))

    try:
        redis = Redis.from_url(settings.redis_url)
        redis.ping()
        queue = Queue("face_jobs", connection=redis)
        workers = Worker.all(connection=redis)
        active_workers = [worker for worker in workers if _worker_is_active(worker)]
        results.append(("Redis", True, "reachable"))
        results.append(("RQ worker", bool(active_workers), f"{len(active_workers)} active"))
        results.append(("Queued snapshots", True, str(len(queue))))
    except Exception as exc:
        results.append(("Redis", False, exc.__class__.__name__))
        results.append(("RQ worker", False, "unknown"))
        results.append(("Queued snapshots", False, "unknown"))

    api_ok, api_detail = _http_status(_api_health_url())
    results.append(("FastAPI", api_ok, api_detail))

    dashboard_url = os.getenv("DASHBOARD_URL", "http://127.0.0.1:8000/")
    dashboard_ok, dashboard_detail = _http_status(dashboard_url)
    results.append(("Django dashboard", dashboard_ok, dashboard_detail))

    device_key_ok = bool(os.getenv("DEVICE_API_KEY", "").strip())
    results.append(
        (
            "Device key",
            device_key_ok,
            "configured" if device_key_ok else "missing",
        )
    )

    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"{'OK' if ok else 'FAIL':4}  {name:<{width}}  {detail}")

    required = [
        ok
        for name, ok, _ in results
        if name != "Queued snapshots"
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
