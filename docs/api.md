# API Reference

This document describes the common HTTP endpoints that a deployment of the Facial Emotion Detection and Logging System can expose. Implementations may vary; adjust paths and auth as needed.

Base URL: http://HOST:PORT/api

Endpoints

- GET /health
  - Purpose: Check service health.
  - Response: 200 OK { "status": "ok", "uptime": "<seconds>" }

- POST /images
  - Purpose: Submit an image for immediate processing.
  - Request: multipart/form-data with field `image` (binary)
  - Response: 202 Accepted { "job_id": "<id>", "message": "queued" }

- GET /jobs/{job_id}
  - Purpose: Query processing job status and result.
  - Response:
    - 200 OK { "job_id": "...", "status": "done|processing|failed", "result": { "face_id": "...", "emotion": "...", "confidence": 0.83 } }

- GET /faces
  - Purpose: List known faces stored in the database.
  - Response: 200 OK [ { "face_id": "...", "created_at": "..." }, ... ]

- GET /faces/{face_id}
  - Purpose: Retrieve metadata and embedding presence for a known face.
  - Response: 200 OK { "face_id": "...", "embedding_stored": true, "first_seen": "..." }

- GET /emotions
  - Purpose: Query logged emotions with optional query params (face_id, from, to, emotion).
  - Query params: face_id, from (ISO), to (ISO), emotion
  - Response: 200 OK [ { "id": 1, "face_id": "...", "detected_emotion": "...", "confidence": 0.9, "timestamp": "..." }, ... ]

Authentication and Security
- Recommend using API keys or JWT for protected endpoints.
- Ensure DB credentials are not exposed; use environment variables or a secrets manager.

Notes
- Responses and exact fields are implementation-specific; use this file as a contract for client/server integration. Add paginated responses where required.
