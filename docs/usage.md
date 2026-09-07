# Development usage

Python 3.10 is recommended because the pinned TensorFlow worker dependency targets
that runtime.

## XAMPP database

Start MySQL in the XAMPP Control Panel, then create the database and a dedicated
application account in the XAMPP shell:

```sql
CREATE DATABASE smart_sentiment
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sentiment_app'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON smart_sentiment.* TO 'sentiment_app'@'localhost';
FLUSH PRIVILEGES;
```

Copy `.env.example` to `.env`, put the same password in `MYSQL_PASSWORD`, and
keep `MYSQL_HOST=127.0.0.1`. Never commit `.env`.

The MariaDB 10.4 series bundled with many XAMPP releases is end-of-life and is
below Django 5.2's officially supported MariaDB 10.5 minimum. The
`XAMPP_ALLOW_MARIADB_10_4=true` compatibility option keeps local XAMPP working,
but upgrading MariaDB is strongly recommended.

Keep `DJANGO_TIME_ZONE=UTC` unless you load named time-zone tables into MariaDB.
UTC and Ghana civil time have the same offset, so Accra timestamps are unchanged.

## Separate local environments

The API/dashboard test environment excludes TensorFlow:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Create a separate Python 3.10 worker environment:

```bash
python -m venv .venv-worker
. .venv-worker/bin/activate
pip install -r api_server/requirements-worker.txt
python -m api_server.worker_main
```

Start the API:

```bash
uvicorn api_server.face_api:app --host 0.0.0.0 --port 8001
```

Start Django from `emotion_dashboard/`:

```bash
python manage.py migrate
python manage.py runserver 8000
```

With `DATABASE_ENGINE=mysql`, Django, the ingestion API, and the worker all use
the XAMPP database. Run migrations before the first start. SQLite remains
available only for isolated tests by setting `DATABASE_ENGINE=sqlite`; the API
and worker require MySQL/MariaDB and Redis.

## Tests

```bash
python -m unittest discover -s tests -v

cd emotion_dashboard
DATABASE_ENGINE=sqlite python manage.py test monitor
```
