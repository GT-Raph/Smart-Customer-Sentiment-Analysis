"""Long-lived RQ worker entry point that retains loaded ML models."""

import logging

from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker

from .config import settings
from .worker import warm_models

logging.basicConfig(level="INFO")


def main() -> None:
    settings.validate()
    connection = Redis.from_url(settings.redis_url)
    connection.ping()
    warm_models()
    worker = SimpleWorker([Queue("face_jobs", connection=connection)], connection=connection)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
