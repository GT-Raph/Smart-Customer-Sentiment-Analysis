# Ingestion API

Base URL for local development: `http://localhost:8001`

Every device request must include the key created by Django:

```http
X-API-Key: scs_<prefix>_<secret>
```

The server stores only the SHA-256 hash of the full key. A key is shown once by
`python manage.py create_device_key` and can be revoked by disabling its Device
record in Django admin.

## `GET /health`

Checks PostgreSQL and Redis. Returns HTTP 503 when either dependency is down.

## `POST /v1/snapshots`

Uploads one cropped face as `multipart/form-data` field `file`.

Accepted formats: JPEG, PNG and WebP. The declared content type must match the
actual file. Byte-size, decoded dimensions and per-device rate limits apply.

The device supplies a short-lived `session_id` so repeated frames during one visit are not counted as different visitors when biometric identification is disabled.

Organisation subscription status and the monthly analysis quota are checked before the job is accepted. A full quota returns HTTP 429.

Successful response:

```json
{
  "job_id": "01J...",
  "status": "queued"
}
```

The legacy path `/upload-face` points to the same handler but is hidden from the
OpenAPI schema.

## `GET /v1/snapshots/{job_id}`

Returns status for a job created by the same device. Devices cannot read jobs
belonging to another device or organisation.

Possible states: `queued`, `processing`, `processed`, `failed`.

## Raw images

There is no public image-listing endpoint. A development-only authenticated
image endpoint exists behind `ENABLE_DEV_IMAGE_ENDPOINT=true`; keep it disabled
in production. The worker deletes raw images after processing by default.
