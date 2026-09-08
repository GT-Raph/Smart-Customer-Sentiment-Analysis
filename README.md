# Smart Customer Sentiment Analysis

A SaaS-ready foundation for privacy-conscious facial-expression analytics. The
system receives a cropped face from a registered device, queues analysis, runs
DeepFace in a separate worker, and displays processed aggregate results in a
Django dashboard. The `main` branch uses one hosted Supabase PostgreSQL database
for the dashboard, ingestion API, and worker; the separate `non-saas` branch is
not merged into it.

> The output is a facial-expression signal, not proof of a person's true
> emotion. Face identification is disabled by default.

## Architecture

```text
Device agent -> FastAPI ingestion -> PostgreSQL job + Redis queue
                                      |
                                      v
                              DeepFace RQ worker
                                      |
                                      v
                              Django dashboard
```

## What was fixed

- Removed committed database credentials and Django secret.
- Replaced optional global API authentication with per-device revocable keys.
- Added organisations, branches, devices and tenant-scoped dashboard access.
- Added subscription states and atomic monthly analysis quotas per organisation.
- Replaced conflicting database definitions with one Django-managed schema.
- Moved DeepFace processing out of the web request and into an RQ worker.
- Added upload type, byte-size, pixel-size and per-device rate limits.
- Removed the public raw-image endpoint and enabled deletion after processing.
- Added safe error responses, job status tracking and failed-job state.
- Added short-lived, non-biometric visit sessions when face identification is disabled.
- Replaced notebook production processing with importable Python modules.
- Added Docker development deployment and basic tests.

## Quick start

Copy `.env.example` to `.env.saas`, paste the Session pooler connection details
from the Supabase **Connect** panel, and then follow
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Existing prototype databases
should follow [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md).

## Main services

- `emotion_dashboard/`: Django SaaS control plane and analytics dashboard.
- `api_server/face_api.py`: authenticated ingestion API.
- `api_server/worker.py`: DeepFace/RQ inference worker.
- `clients/device_agent.py`: low-rate reference camera client.

## Commercial SaaS work remaining

Payment-provider integration, customer onboarding, audit-log UI, data export/deletion UI,
object storage, webhooks, model-quality monitoring, legal documentation and
production observability remain to be implemented.
