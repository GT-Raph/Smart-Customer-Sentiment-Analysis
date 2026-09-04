# Deployment

## Local Docker development

```bash
cp .env.example .env
# Change DJANGO_SECRET_KEY and the database password in both .env and docker-compose.yml
docker compose up --build
```

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
- Use a managed PostgreSQL database and managed Redis.
- Set `DJANGO_DEBUG=false`, real hosts, trusted origins and HTTPS settings.
- Use separate API and worker autoscaling policies.
- Add centralized logs, metrics, error tracking, backups and recovery tests.
- Add billing, quotas and customer self-service before commercial launch.
