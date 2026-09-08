# Deployment

## Configure Supabase

The `main` branch reads the root `.env` file. In the Supabase dashboard, open
**Connect**, choose the Session pooler, and copy its values into `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. Keep
`DB_ENGINE=postgresql` and `DB_SSLMODE=require`.

The separate fields are recommended because the application safely URL-encodes
password punctuation internally.

Verify the connection and migration state:

```powershell
cd emotion_dashboard
python manage.py showmigrations monitor
python manage.py makemigrations --check --dry-run
python manage.py migrate
```

The existing SaaS database should show `monitor.0001_initial` and
`monitor.0002_bank_api_key_rotated_at_alter_bank_code_and_more` as applied.
Back up production data before applying any future migration.

## Configure a tenant

Create the first platform administrator if needed:

```powershell
python manage.py createsuperuser
```

In Django admin, create or review the bank and its branches. Every teller PC
must match an active branch's PC-name prefix. Set or rotate a bank upload key:

```powershell
python manage.py set_bank_api_key FIDELITY_GH
```

The raw key is displayed once; store it as `BANK_API_KEY` on the teller client.
Do not distribute Supabase credentials or `DJANGO_SECRET_KEY` to teller PCs.

## Run without Docker

From `emotion_dashboard/`:

```powershell
python manage.py runserver 0.0.0.0:8000
```

From the repository root:

```powershell
python -m uvicorn api_server.face_api:app --host 0.0.0.0 --port 8001
```

The health endpoint is `http://127.0.0.1:8001/health`.

## Docker development

```powershell
docker compose up --build
```

Compose starts Django and FastAPI, passes the same Supabase configuration to
both, and shares the private `captured_faces` volume. It does not create or
replace the hosted database.

## Production requirements

- Set `DJANGO_DEBUG=False`, real allowed hosts, trusted HTTPS origins, and secure
  proxy/cookie settings.
- Keep secrets in the hosting platform's secret store, not in source control.
- Replace the shared local image volume with private object storage before
  scaling across hosts.
- Put Django and FastAPI behind HTTPS, add monitoring/backups, and define image
  and biometric-data retention policies.
