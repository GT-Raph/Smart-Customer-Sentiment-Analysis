# Architecture

```text
Reference camera client
        |
        | device API key + cropped image
        v
FastAPI ingestion service
        |-- validates image and rate limit
        |-- writes a queued job to XAMPP MariaDB
        `-- enqueues the job in Redis/RQ
                    |
                    v
Long-lived DeepFace worker
        |-- expression analysis
        |-- optional installation-wide face matching
        |-- deletes raw images by default
        `-- stores the result and terminal status
                    |
                    v
Django local dashboard/admin
        |-- physical branches
        |-- local users and branch access
        |-- registered/revocable devices
        `-- processed aggregate analytics
```

## Deployment boundary

One deployment belongs to one organization. There is no tenant selector, billing
account, subscription status, plan, or analysis quota. Deploy a separate instance
and database when another organization needs the system.

## Ownership boundaries

- Django migrations own the relational schema.
- FastAPI handles ingestion and does not load TensorFlow.
- The RQ worker performs inference and keeps models warm.
- Redis is transient queue infrastructure; MariaDB stores jobs and results.
- The included shared volume supports a one-host installation.

## Privacy and security defaults

- Persistent face identification is off by default.
- Raw images are deleted after successful analysis by default.
- Every camera is authenticated with a revocable device API key.
- Normal dashboard users only see their assigned branch.
- Results are expression signals, not verified internal emotions.
