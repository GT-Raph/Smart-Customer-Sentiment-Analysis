# Architecture

```text
Reference camera client
        |
        | device API key + cropped image
        v
FastAPI ingestion service
        |-- validates image and rate limit
        |-- writes queued job to PostgreSQL
        `-- enqueues job in Redis/RQ
                    |
                    v
Long-lived DeepFace worker
        |-- expression analysis
        |-- optional organisation-scoped face matching
        |-- deletes raw image by default
        `-- stores result and terminal status
                    |
                    v
Django SaaS dashboard/admin
        |-- organisations and branches
        |-- users and tenant access
        |-- registered/revocable devices
        `-- processed aggregate analytics
```

## Ownership boundaries

- Django migrations own the relational schema.
- FastAPI handles ingestion only and does not load TensorFlow.
- The worker performs model inference and keeps models warm in a long-lived
  process.
- Redis is transient job infrastructure; PostgreSQL is the job/result record.
- Local shared storage is supported for one-host deployment. Multi-host
  production requires private object storage.

## Privacy defaults

- Persistent face identification is off by default; the reference client uses short-lived visit sessions instead.
- Raw images are deleted after successful analysis by default.
- A device is bound to one organisation and branch.
- Subscription status and monthly organisation quotas are enforced before queueing.
- An unassigned dashboard user is denied instead of receiving unfiltered data.
- Results are described as expression signals, not verified internal emotions.
