# Self-hosted deployment

## Docker Compose

Copy the example environment and replace every placeholder secret:

```bash
cp .env.example .env
docker compose up --build -d
```

Create the local administrator:

```bash
docker compose exec dashboard python manage.py createsuperuser
```

Open `http://localhost:8000/admin/`, sign in, and create at least one Branch.
Then create a key for each camera, using the branch ID shown in Django admin:

```bash
docker compose exec dashboard python manage.py create_device_key \
  --branch 1 --name front-desk-camera --pc-name ACCRA01-CAMERA
```

Copy the printed key immediately into `DEVICE_API_KEY` on that camera computer.
It cannot be displayed again. Set `INGESTION_API_URL` to the API address and run:

```bash
python clients/device_agent.py
```

The dashboard is served on port 8000 and the ingestion API on port 8001.
Docker Compose overrides `DJANGO_USE_SQLITE=false`, so every service shares the
PostgreSQL database.

## Production checklist

- Set `DJANGO_DEBUG=false` and configure real hosts, trusted origins, and HTTPS.
- Restrict ports 5432 and 6379 to the application network.
- Use strong, unique database and Django secrets.
- Back up PostgreSQL and test restoration regularly.
- Configure centralized logs, monitoring, and error reporting.
- Use private object storage if services run on more than one host.
- Review consent, retention, and biometric-data requirements for your jurisdiction.
