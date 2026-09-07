# Smart Customer Sentiment Analysis

A self-hosted, non-SaaS application for privacy-conscious facial-expression
analytics. A registered camera device sends a cropped face to the ingestion API,
analysis runs in a background worker, and authorized staff view aggregate results
in the Django dashboard.

> The output is a facial-expression signal, not proof of a person's true
> emotion. Face identification is disabled by default.

## Non-SaaS design

This branch is designed for one organization to operate on its own infrastructure.
It has no customer tenants, plans, subscriptions, billing records, or monthly usage
quotas. Branches represent the organization's physical locations and are retained
for access control and comparison reports.

Device API keys, authenticated dashboard users, upload limits, and privacy controls
remain in place because they are security features rather than SaaS features.
The dashboard templates, navigation, analytics pages, charts, branding, and
responsive styling intentionally retain the SaaS edition's user experience.

## Architecture

```text
Camera agent -> FastAPI ingestion -> PostgreSQL + Redis queue
                                           |
                                           v
                                  DeepFace RQ worker
                                           |
                                           v
                                   Django dashboard
```

## Quick start

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). If migrating a database created by
the SaaS branch, read [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) first.

## Main services

- `emotion_dashboard/`: local administration and analytics dashboard.
- `api_server/face_api.py`: authenticated image-ingestion API.
- `api_server/worker.py`: DeepFace/RQ inference worker.
- `clients/device_agent.py`: low-rate reference camera client.
