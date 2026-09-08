# Ingestion API

Local base URL: `http://127.0.0.1:8001`

## Authentication

Every upload includes the bank code and the raw upload key:

```http
X-Bank-Code: FIDELITY_GH
X-API-Key: <bank-upload-key>
```

Create or rotate a key from the Django project directory with:

```powershell
python manage.py set_bank_api_key FIDELITY_GH
```

The database stores only its hash.

## `GET /health`

Checks the Supabase PostgreSQL connection. It returns HTTP 200 when healthy and
HTTP 503 when the database is unavailable.

## `POST /upload-face`

Uploads one image as `multipart/form-data`:

- `file`: JPEG, PNG, or WebP image.
- `pc_name`: Windows computer name, 1-128 characters.

The API authenticates the bank, finds the longest matching active branch PC
prefix, validates the image and size, runs face/expression analysis, stores the
snapshot, and returns HTTP 201.

Example response shape:

```json
{
  "status": "processed",
  "job_id": "01...",
  "bank": {"code": "FIDELITY_GH", "name": "..."},
  "branch": {"code": "...", "name": "...", "matched_pc_prefix": "..."},
  "pc_name": "ACCRA01-PC01",
  "faces": []
}
```

An unknown PC prefix returns HTTP 403. Invalid authentication returns HTTP 401;
invalid images return a safe 4xx response. There is no public raw-image listing
endpoint.
