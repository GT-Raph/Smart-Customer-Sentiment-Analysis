# Development usage

Python 3.10 is recommended because the pinned TensorFlow worker dependency targets
that runtime.

## Docker path

```bash
cp .env.example .env
# Set a random POSTGRES_PASSWORD and DJANGO_SECRET_KEY
docker compose up --build
```

Then create an administrator, a branch, and a device key as described in
`DEPLOYMENT.md`. No organization or subscription record is required.

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

## Tests

```bash
python -m unittest discover -s tests -v

cd emotion_dashboard
DJANGO_DEBUG=true DJANGO_SECRET_KEY=test-only \
DATABASE_URL=sqlite:////tmp/sentiment-tests.sqlite3 \
python manage.py test monitor
```
