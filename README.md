# Smart Customer Sentiment Analysis

A multi-bank SaaS application for customer facial-expression analytics. Teller
camera clients upload cropped face images to an authenticated FastAPI service,
the service records tenant-scoped results in Supabase PostgreSQL, and authorized
bank users view analytics in the Django dashboard.

> The output is a facial-expression signal, not proof of a person's true
> emotion. Deploy only with an appropriate privacy, consent, and retention
> policy.

The `main` branch is the hosted Supabase SaaS product. The separate `non-saas`
branch uses its own local deployment design and has not been merged into
`main`.

## Architecture

```text
Teller camera -> FastAPI /upload-face -> DeepFace analysis
                       |                       |
                       `------ Supabase ------'
                                  |
                           Django dashboard
```

Each request supplies a bank code and API key. The Windows computer name is
matched to the longest active PC prefix configured for one of that bank's
branches. Django access is tenant-scoped for platform administrators, bank
administrators, and branch users.

## Quick start

1. Copy `.env.example` to `.env` and enter the Supabase Session pooler values.
2. Install `requirements.txt` in a Python 3.10 virtual environment.
3. Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

All server-side components read the root `.env` file. Password punctuation is
handled safely by the separate `DB_*` settings; no manually assembled database
URL is required.

## Main components

- `emotion_dashboard/`: Django SaaS dashboard, admin, tenancy, and migrations.
- `api_server/face_api.py`: bank-authenticated ingestion and analysis API.
- `desktop_capture.py`: production-oriented teller camera client.
- `clients/device_agent.py`: smaller reference camera client.
- `captured_faces/`: private, shared local image storage (gitignored).

## Commercial work remaining

Billing/subscriptions, self-service customer onboarding, private object storage,
audit logs, data export/deletion workflows, production observability, and formal
model/privacy validation remain before a public commercial launch.
