# Deployment

## Supabase configuration

The active branch reads its configuration from the root `.env` file. On
`main`, that file must contain the Supabase settings shown in `.env.example`.

1. In the Supabase dashboard, open **Connect** and copy the Session pooler
   connection string (port `5432`) for a persistent Django/API deployment.
2. Copy `.env.example` to `.env`.
3. Put the connection string in `SUPABASE_DB_URL`, retain
   `?sslmode=require`, and replace the other placeholder secrets.

If the database password contains URL punctuation, either URL-encode it or use
the separate `SUPABASE_DB_*` variables shown in `.env.example`.

Before starting the services, verify the connection and apply migrations:

```bash
cd emotion_dashboard
python manage.py migrate
python manage.py showmigrations monitor
```

Both commands must complete against Supabase. Do not continue if Django reports
an authentication, DNS, SSL, or migration error.

## Local Docker development

```bash
cp .env.example .env
# Add the Supabase connection and replace DJANGO_SECRET_KEY in .env
docker compose up --build
```

Docker Compose runs Redis locally, but it does not create or override the
PostgreSQL database. Django, FastAPI, and the worker all receive the same
Supabase configuration from `.env`.

Create the first administrator:

```bash
docker compose exec dashboard python manage.py createsuperuser
```

In Django admin, create an organisation and branch. Then create a device key:

```bash
docker compose exec dashboard python manage.py create_device_key \
  --organization demo-company --branch 1 --name front-desk-camera \
  --pc-name ACCRA01-CAMERA
```

Put the printed key into the client machine's `DEVICE_API_KEY` environment
variable and run `python clients/device_agent.py` from a local Python 3.10
environment with OpenCV, Requests and python-dotenv installed.

## Production changes still required

- Replace the shared Docker volume with private S3/R2/GCS-compatible storage.
- Keep Supabase PostgreSQL and use a managed Redis service.
- Set `DJANGO_DEBUG=false`, real hosts, trusted origins and HTTPS settings.
- Use separate API and worker autoscaling policies.
- Add centralized logs, metrics, error tracking, backups and recovery tests.
- Add billing, quotas and customer self-service before commercial launch.
