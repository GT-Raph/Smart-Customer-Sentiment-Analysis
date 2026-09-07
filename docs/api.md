# Ingestion API

Base URL for local operation: `http://localhost:8001`

Every camera request must include the key created by Django:

```http
X-API-Key: scs_<prefix>_<secret>
```

Only a SHA-256 hash of the full key is stored. The key is shown once by
`python manage.py create_device_key` and can be revoked by disabling its Device
record in Django admin.

## `GET /health`

Checks XAMPP MySQL/MariaDB and Redis. It returns HTTP 503 when either dependency is down.

## `POST /v1/snapshots`

Uploads one cropped face as the `file` field in `multipart/form-data`. JPEG, PNG,
and WebP are accepted. Declared and actual types must match. Byte-size, image
dimensions, and per-device rate limits apply.

The optional `session_id` identifies repeated frames from one visit when biometric
identification is disabled. The non-SaaS edition does not apply subscription or
monthly usage limits.

Successful response:

```json
{
  "job_id": "01J...",
  "status": "queued"
}
```

## `GET /v1/snapshots/{job_id}`

Returns the status of a job created by the same device. Possible states are
`queued`, `processing`, `processed`, and `failed`.

## Raw images

There is no public image listing. A development-only authenticated endpoint is
available behind `ENABLE_DEV_IMAGE_ENDPOINT=true`. Keep it disabled outside local
development. The worker deletes raw images after processing by default.
