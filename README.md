# Smart Customer Sentiment Analysis

<p align="center">
  Multi-bank SaaS for privacy-conscious customer facial-expression analytics.
</p>

<p align="center">
  <img alt="Python 3.10" src="https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white">
  <img alt="Django 5.2" src="https://img.shields.io/badge/Django-5.2-0C4B33?logo=django&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white">
  <img alt="Supabase PostgreSQL" src="https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase&logoColor=white">
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-blue.svg">
</p>

---

# Overview

Smart Customer Sentiment Analysis is a multi-bank SaaS application for collecting and analysing customer facial-expression signals at teller workstations.

A teller camera client selects a usable customer face, then sends it to an authenticated FastAPI service. The API identifies the tenant and branch, performs face matching and expression analysis with DeepFace, stores the result in Supabase PostgreSQL, and exposes tenant-scoped analytics through a Django dashboard.

The application is designed around four boundaries:

- Each bank is an independent SaaS tenant.
- A bank's visitors, branches, snapshots, settings, and users remain isolated from other banks.
- Teller computers receive upload credentials only; they never receive Supabase or Django secrets.
- Captured images are private application data and are never served as public media.

> [!IMPORTANT]
> The model estimates visible facial expressions. It does not prove what a person feels, thinks, or intends. Do not use its output to make lending, employment, security, legal, or other high-impact decisions.

---

# SaaS Deployment Model

The `main` branch is the hosted multi-tenant SaaS product:

```text
One application deployment
        |
        +---- Bank A tenant
        |       +---- Branches
        |       +---- Users
        |       +---- Visitors
        |       `---- Analytics
        |
        +---- Bank B tenant
        |       +---- Branches
        |       +---- Users
        |       +---- Visitors
        |       `---- Analytics
        |
        `---- Platform administrators
```

The `non-saas` branch is a separate local-installation product. It uses a different database, device-authentication, processing, and deployment design.

Do not merge either branch wholesale into the other. Share an individual fix only after reviewing its tenant, database, API, migration, and deployment assumptions.

The current SaaS codebase implements the tenant-aware application core. Billing, subscriptions, self-service tenant onboarding, and other commercial platform services are still future work.

---

# Architecture

## Architectural Style

```text
Customer at teller counter
          |
          v
Teller camera workstation
desktop_capture.py
          |
          | HTTPS multipart upload
          | X-Bank-Code + X-API-Key + PC name
          v
FastAPI ingestion service
          |
          +---- validates tenant credentials
          +---- resolves branch from PC-name prefix
          +---- validates and stores the image
          +---- performs DeepFace analysis synchronously
          +---- matches or creates a tenant-scoped visitor
          `---- writes the snapshot transactionally
                          |
                          v
               Supabase PostgreSQL
                          |
                          v
                 Django dashboard
          platform admin / bank admin / branch user
```

Django and FastAPI read the same root `.env` and connect to the same Supabase PostgreSQL schema. The camera client communicates only with FastAPI.

## Ownership Boundaries

| Concern | Owner |
|---|---|
| Relational schema and migrations | Django |
| Tenant, user, branch, visitor, and snapshot records | Supabase PostgreSQL |
| Upload authentication and branch resolution | FastAPI |
| Face embedding and expression analysis | FastAPI with DeepFace |
| Dashboard authorization and reporting | Django |
| Camera acquisition and frame-quality selection | Teller desktop client |
| Captured image bytes | Private server-side storage |

Django migrations are the only supported way to evolve the shared database schema. Avoid creating application tables manually in Supabase.

---

# Runtime Components

## Django Dashboard

The Django application under `emotion_dashboard/` provides:

- Session-based authentication and password-reset routes.
- Platform, bank, and branch authorization boundaries.
- Dashboard totals, trends, hourly activity, and emotion distributions.
- Branch comparison and branch-detail views.
- Visitor search, visitor detail, and visit history.
- Tenant-scoped CSV reports.
- User, dashboard, notification, bank, and branch settings.
- Tenant-authorized image delivery.
- A platform-superuser-only Django admin.

## FastAPI Ingestion Service

`api_server/face_api.py` provides the upload boundary. It:

- Requires a bank code and bank upload key.
- Rejects inactive or invalid tenants.
- Resolves a branch from the longest active PC-name prefix within that bank.
- Accepts JPEG, PNG, and WebP within the configured size limit.
- Decodes and validates the image before processing.
- Limits concurrent face-processing work.
- Stores accepted images under tenant and branch directories.
- Runs face extraction, embeddings, matching, and expression analysis.
- Commits visitor and snapshot records in a database transaction.
- Removes the stored image when processing fails.

## DeepFace Runtime

The SaaS branch processes uploads synchronously inside FastAPI; it does not use a separate Redis/RQ worker.

DeepFace is imported lazily so the API can start and expose basic service information before the ML runtime is first needed. The configured embedding model defaults to ArcFace.

## Production Desktop Capture Client

The root `desktop_capture.py` is the feature-complete teller client. It supports:

- Customer-region-of-interest calibration.
- Exactly-one-face selection.
- Minimum size, blur, brightness, and exposure gates.
- Face-position stability checks.
- Candidate sampling and best-frame selection.
- Background uploads.
- Duplicate-interaction suppression.
- A bounded offline retry queue.
- Optional live preview for installation and calibration.

The preview currently defaults to enabled. Set `PREVIEW_ENABLED=false` only after the camera position and quality thresholds have been calibrated and the deployment's consent/notice process is in place.

## Reference Camera Client

`clients/device_agent.py` is a smaller reference implementation. It crops the largest detected face, applies a capture interval, and maintains a small local retry queue. It does not provide the production client's full ROI, stability, and quality-selection workflow.

## Supabase PostgreSQL

Supabase PostgreSQL is the authoritative shared database for the `main` branch. Both server applications use TLS and the same connection values.

For typical hosted deployment, use the Supabase Session pooler values shown under **Project → Connect**.

## Private Image Storage

The default development path is `captured_faces/`. Database rows store relative paths, while Django serves files only through an authenticated, tenant-filtered view.

Local shared storage works for a one-host deployment. A multi-host production deployment needs private object storage or another shared private file service.

---

# Tenant Access and Authorization

## Platform Administrators

A Django superuser can:

- View all active banks and branches.
- Compare tenants and branches where the UI exposes those scopes.
- Manage banks, branches, users, settings, and visitors, and review read-only snapshots in Django admin.
- Create the initial tenant structure.
- Rotate a bank upload key.

Django admin is intentionally restricted to platform superusers.

## Bank Administrators

A normal user with a bank and no branch is a bank administrator. They can:

- View all active branches belonging to their bank.
- Compare branches within their bank.
- View their bank's visitors, snapshots, history, and reports.
- Manage their bank and branch settings through the application settings page.
- Rotate their bank's upload key.

They cannot view or manage another bank.

## Branch Users

A user assigned to a branch can:

- View only that branch's snapshots and analytics.
- View visitors only when those visitors have snapshots visible in the assigned branch.
- Export only records from the assigned branch.
- Update personal settings.

A branch user cannot access installation-wide or bank-wide comparison operations.

## Unassigned Users

A non-superuser without a valid bank assignment receives no tenant data. Model validation also prevents newly saved normal users from remaining unassigned.

## Authorization Enforcement

Tenant restrictions are applied by server-side helpers in `emotion_dashboard/monitor/tenant.py`:

```text
visible_branches(user)
visible_snapshots(user)
visible_visitors(user)
get_visible_branch_or_404(user, branch_id)
require_bank_admin(user)
```

Hiding navigation links is not treated as authorization. Querysets and private image responses are scoped on the server.

---

# Authentication

## Dashboard Authentication

The dashboard uses Django sessions and the custom `monitor.CustomUser` model. Password validation, CSRF protection, secure-cookie production defaults, clickjacking protection, and password-reset routes are configured.

In development, password-reset email is printed to the console. Production requires an explicit email backend.

## Upload Authentication

Each upload includes:

```http
X-Bank-Code: YOUR_BANK_CODE
X-API-Key: your-bank-upload-key
```

Bank codes are normalized to uppercase. Raw keys must contain at least 24 characters and are stored only as SHA-256 hashes. Comparison uses a constant-time digest check.

Rotate a key from the dashboard settings page or with the management command. Rotation immediately invalidates the previous key for every teller computer in that bank.

## Branch Identification

The teller client does not choose a branch ID. FastAPI uses the authenticated bank and the Windows computer name:

```text
Authenticated bank: FIDELITY_GH
Computer name:      FBLRIDGE003
Configured prefixes:
  FBL          -> Head Office
  FBLRIDGE     -> Ridge Branch

Result: Ridge Branch, because the longest active prefix wins.
```

PC prefixes are unique within each bank, preventing ambiguous tenant-local assignments.

---

# Core Data Model

## Bank

Represents the top-level SaaS tenant.

```text
name
code                         globally unique tenant code
api_key_hash                 upload secret digest
api_key_rotated_at           last key rotation time
is_active
created_at
```

## Branch

Represents a physical branch belonging to one bank.

```text
bank
name
code                         unique within bank
pc_prefix                    unique within bank
location
is_active
```

## CustomUser

Extends Django's user with optional `bank` and `branch` relationships.

```text
superuser                    platform administrator
bank set, branch empty       bank administrator
bank set, branch set         branch user
```

When a branch is assigned, the user's bank is automatically aligned to the branch's bank.

## BankSettings

Stores one settings record per bank:

```text
timezone
image_retention_days
record_retention_days
delete_images_after_retention
offline_after_minutes
updated_at
```

The settings currently record retention intentions. Automated retention deletion still needs an operational scheduled task.

## UserPreference

Stores dashboard defaults and notification preferences:

```text
default date and hourly ranges
default branch
auto-refresh interval
compact mode
reduced motion
weekly-summary preference
negative-emotion notification preference
negative threshold
minimum detection count
```

The UI stores notification preferences, but outbound scheduled notification delivery is not yet implemented.

## Visitor

Represents a bank-scoped face identity.

```text
bank
face_id                      unique within bank
first_seen
last_seen
```

Face matching never intentionally crosses a tenant boundary.

## CapturedSnapshot

Represents one processed capture:

```text
job_id                       globally unique request identifier
bank
branch
visitor
pc_name
image_path                   relative private-storage path
timestamp
emotion
confidence
emotion_vector
embedding
processed
status                       pending / done / failed
processing_error
```

Model validation prevents a snapshot from linking a bank to a branch or visitor owned by another bank.

---

# Capture and Analysis Pipeline

## Camera Acquisition

The production client follows this decision path:

```text
Read camera frame
      |
      v
Crop configured customer ROI
      |
      v
Detect faces
      |
      +---- none or multiple ----> wait
      |
      `---- exactly one
                 |
                 v
          quality and size checks
                 |
                 v
          stability across frames
                 |
                 v
          collect good candidates
                 |
                 v
          choose the best frame
                 |
                 v
          background API upload
                 |
                 v
          wait for customer exit
```

Do not upload every camera frame. The selection process reduces bandwidth, redundant rows, and low-quality model inputs.

## Client Quality Gate

The production client evaluates:

- Face width, height, and frame-area ratio.
- Laplacian blur score.
- Average brightness.
- Dark and bright pixel fractions.
- Stable face position using intersection over union.
- Candidate sharpness, exposure, size, and basic eye visibility.

Thresholds are starting values, not universal truth. Calibrate them on the actual camera, lighting, counter distance, and expected range of users.

## Ingestion Validation

FastAPI validates:

- Bank code and upload key.
- Active bank and active branch.
- Safe normalized computer name.
- Supported declared content type.
- Configured byte limit.
- Successfully decoded image data.
- Safe private-storage path.
- Available processing capacity.

## Face Extraction and Embedding

DeepFace extracts faces with enforced detection. Each usable face is enhanced and represented using the configured embedding model.

Candidate embeddings are loaded only from the authenticated bank. Vectors with incompatible dimensions or invalid values are skipped. The closest valid candidate below `MATCH_THRESHOLD` is reused; otherwise a new tenant-local face ID is created.

## Expression Classification

DeepFace returns a dominant expression and score vector. The application stores both the dominant label and numeric confidence.

Expected model categories can include:

```text
angry
disgust
fear
happy
sad
surprise
neutral
```

Dashboard summaries focus primarily on happy, neutral, sad, angry, and surprise. The output is probabilistic and must be presented as an expression estimate.

## Transaction and Failure Handling

Visitor creation/update and snapshot insertion occur within one database transaction. A processing error rolls the transaction back and removes the newly stored image.

Retryable service failures return a safe 5xx response. Validation and model rejections return a 4xx response so desktop clients do not retry invalid captures forever.

---

# Dashboard and Analytics

## Dashboard Overview

The main dashboard provides:

- Today's visitor count.
- Top detected expression.
- Negative-expression percentage.
- Today's activity and peak time.
- Expression distribution.
- Trend data for the selected period.
- Recent tenant-authorized captures.

Users can apply permitted branch and time-range filters. User preferences can provide default filters and optional auto-refresh.

## Branch Overview

Available to platform and bank administrators. It compares permitted branches by visitor volume, dominant expression, positivity, and trend.

## Branch Detail

Displays scoped metrics and recent captures for a single permitted branch.

## Emotion Analytics

Provides time-series, distribution, hourly, and comparison views for tenant-authorized data.

## Visitors and Visit History

Visitors can be searched by face ID. Visitor detail summarizes visible visits and expression distribution. Visit history groups activity by visitor, branch, and day and supports CSV export.

## Reports

Reports export a tenant-scoped date range containing bank, branch, visitor ID, PC, expression, confidence, and timestamp.

## Settings

The settings area supports:

- Profile and password changes.
- Dashboard defaults and accessibility preferences.
- Notification preferences.
- Bank retention and offline-status settings.
- Branch details and PC prefixes.
- Bank upload-key rotation.

Bank and branch management operations are limited to platform and bank administrators.

---

# Ingestion API

Local base URL:

```text
http://127.0.0.1:8001
```

## `GET /`

Returns basic service metadata.

## `GET /health`

Runs a PostgreSQL `SELECT 1` health check.

```text
200  API and database are available
503  database is unavailable
```

## `POST /upload-face`

Multipart request:

```text
Headers:
  X-Bank-Code
  X-API-Key

Form:
  pc_name

File:
  file                        JPEG, PNG, or WebP
```

Successful processing returns HTTP `201 Created` with the job, tenant, branch, PC, and processed-face results.

Typical error responses:

| Status | Meaning |
|---:|---|
| `400` | Invalid PC name, path, or image bytes |
| `401` | Missing or invalid bank credentials |
| `403` | Computer does not match an active branch |
| `413` | Upload exceeds the configured limit |
| `415` | Unsupported media type |
| `422` | Face or expression processing rejected the image |
| `503` | Database, ML runtime, or processing capacity unavailable |

There is no public raw-image listing endpoint.

---

# Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10 |
| Dashboard | Django 5.2 |
| API | FastAPI and Uvicorn |
| Hosted database | Supabase PostgreSQL |
| Database driver | psycopg2 |
| Face analysis | DeepFace 0.0.100 |
| ML runtime | TensorFlow 2.21 and tf-keras |
| Image processing | OpenCV, Pillow, NumPy |
| Matching | SciPy distance utilities |
| Camera networking | Requests |
| Production WSGI | Gunicorn |
| Containerization | Docker Compose |
| Tests | unittest and Django test runner |
| CI | GitHub Actions |

---

# Repository Structure

```text
Smart-Customer-Sentiment-Analysis-fixed/
|
|-- api_server/
|   |-- api/
|   |   `-- index.py                 deployment adapter
|   |-- config.py                    Supabase and API configuration
|   |-- db_utils.py                  tenant-aware SQL operations
|   |-- face_api.py                  FastAPI and DeepFace pipeline
|   |-- face_utils.py                embedding matching and enhancement
|   `-- requirements.txt
|
|-- clients/
|   `-- device_agent.py              compact reference camera client
|
|-- emotion_dashboard/
|   |-- emotion_dashboard/
|   |   |-- settings.py
|   |   `-- urls.py
|   |-- monitor/
|   |   |-- management/commands/
|   |   |-- migrations/
|   |   |-- templates/
|   |   |-- admin.py
|   |   |-- forms.py
|   |   |-- models.py
|   |   |-- settings_views.py
|   |   |-- tenant.py
|   |   |-- urls.py
|   |   `-- views.py
|   `-- manage.py
|
|-- research/
|   `-- legacy_notebooks/            supervised experiments only
|
|-- tests/                            API and camera unit tests
|-- desktop_capture.py               production teller capture client
|-- docker-compose.yml
|-- Dockerfile.api
|-- Dockerfile.dashboard
|-- requirements.txt
|-- .env.example
|-- docs/
|-- LICENSE
|-- README.md
|
|-- captured_faces/                  runtime private files; ignored
`-- offline_queue/                   client retry files; ignored
```

---

# Application Routes

## Dashboard

| Method | Route | Purpose |
|---|---|---|
| GET/POST | `/` | Sign in |
| GET | `/logout/` | Sign out |
| GET | `/dashboard/` | Tenant dashboard |
| GET | `/branches/` | Permitted branch comparison |
| GET | `/branch/<id>/` | Permitted branch detail |
| GET | `/emotion-analytics/` | Expression analytics |
| GET | `/visitors/` | Scoped visitor list |
| GET | `/visitors/<id>/` | Scoped visitor detail |
| GET | `/visit-history/` | Visit history and export |
| GET/POST | `/reports/` | Report form and CSV export |
| GET/POST | `/settings/` | User, tenant, and branch settings |
| GET | `/snapshot/<id>/image/` | Authorized private image |

## Authentication and Administration

| Route | Purpose |
|---|---|
| `/admin/` | Platform-superuser Django admin |
| `/password-reset/` | Request password reset |
| `/password-reset/done/` | Reset-request confirmation |
| `/reset/<uid>/<token>/` | Choose a new password |
| `/reset/done/` | Reset completion |

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Service metadata |
| GET | `/health` | Database health |
| POST | `/upload-face` | Authenticated capture processing |

---

# Environment Configuration

All server components load the root `.env` by default. `APP_ENV_FILE` can point to an alternative environment file when a deployment platform requires it.

Copy the committed template:

```powershell
Copy-Item .env.example .env
```

Never commit the resulting `.env`.

## Django

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-value
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=dashboard.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dashboard.example.com
TIME_ZONE=Africa/Accra
DJANGO_SECURE_SSL_REDIRECT=True
```

When `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` and `EMAIL_BACKEND` are required. Secure cookies, HTTPS redirect, HSTS, and proxy HTTPS handling are then enabled.

## Supabase PostgreSQL

Recommended separate fields:

```dotenv
DB_ENGINE=postgresql
DB_NAME=postgres
DB_USER=postgres.PROJECT_REF
DB_PASSWORD=replace-with-your-database-password
DB_HOST=aws-0-REGION.pooler.supabase.com
DB_PORT=5432
DB_SSLMODE=require
DB_CONN_MAX_AGE=60
DB_CONNECT_TIMEOUT_SECONDS=10
```

Separate fields safely support passwords containing `/`, `*`, `$`, `+`, and other URL punctuation.

The aliases `SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, and `SUPABASE_DB_SSLMODE` are also supported.

A complete `SUPABASE_DB_URL` or `DATABASE_URL` may be used instead, but special characters in its username or password must be URL-encoded.

## Face Analysis and Storage

```dotenv
EMBEDDING_MODEL=ArcFace
MATCH_THRESHOLD=0.45
MAX_UPLOAD_BYTES=5242880
MAX_EMBEDDING_CANDIDATES=5000
FACE_PROCESSING_CAPACITY_WAIT_SECONDS=2
CAPTURED_FACES_ROOT=captured_faces
```

## Teller Identity

Teller computers need only client configuration:

```dotenv
FACE_API_URL=https://api.example.com/upload-face
BANK_CODE=YOUR_BANK_CODE
BANK_API_KEY=replace-with-the-bank-upload-key
```

Do not place `DJANGO_SECRET_KEY`, Supabase credentials, or server storage settings on teller PCs.

## Production Capture Client

Common settings:

```dotenv
CAMERA_INDEX=0
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=30
MAX_CONSECUTIVE_READ_FAILURES=30
REQUEST_TIMEOUT_SECONDS=90
PREVIEW_ENABLED=true
UPLOAD_FACE_CROP=true
JPEG_QUALITY=92

ROI_LEFT=0.18
ROI_TOP=0.06
ROI_RIGHT=0.82
ROI_BOTTOM=0.96

MIN_FACE_WIDTH_PIXELS=120
MIN_FACE_HEIGHT_PIXELS=120
MIN_FACE_AREA_RATIO=0.035
BLUR_THRESHOLD=45
MIN_BRIGHTNESS=45
MAX_BRIGHTNESS=215
MAX_DARK_PIXEL_FRACTION=0.58
MAX_BRIGHT_PIXEL_FRACTION=0.38

STABLE_FRAMES_REQUIRED=6
STABILITY_IOU_THRESHOLD=0.55
SAMPLE_WINDOW_SECONDS=1.2
MIN_GOOD_CANDIDATES=4
DETECTION_INTERVAL_FRAMES=2
FACE_ABSENCE_RESET_SECONDS=1.8
CAPTURE_COOLDOWN_SECONDS=5

OFFLINE_QUEUE_DIR=offline_queue
QUEUE_RETRY_INTERVAL_SECONDS=30
MAX_OFFLINE_QUEUE_FILES=300
REJECTED_CAPTURE_RETENTION_SECONDS=86400
```

Calibrate these values per workstation type. Do not silently deploy default thresholds as if they had been validated for every bank environment.

---

# Local Development

## Requirements

- Windows 10 or later for teller-camera testing.
- Python 3.10.
- Git.
- A Supabase project and PostgreSQL Session pooler credentials.
- A supported webcam for capture testing.
- Docker Desktop only if using Compose.

The ML packages are large. Ensure adequate disk space and allow time for DeepFace model downloads on first use.

## 1. Clone the Repository

```powershell
git clone https://github.com/GT-Raph/Smart-Customer-Sentiment-Analysis.git
cd Smart-Customer-Sentiment-Analysis
git switch main
```

## 2. Create the Environment

```powershell
py -3.10 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Use the virtual-environment Python explicitly if activation is unavailable:

```powershell
.\.venv\Scripts\python.exe --version
```

## 3. Configure `.env`

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Fill in the Supabase Session pooler, Django, and local client values. Keep the root `.env` private.

## 4. Verify Supabase Connectivity

From the repository root:

```powershell
.\.venv\Scripts\python.exe -c "from api_server.db_utils import db_healthcheck; print(db_healthcheck())"
```

If this fails, confirm:

- The Supabase project is running.
- Session pooler host, user, and port match the dashboard.
- The password is copied exactly into `DB_PASSWORD`.
- `DB_SSLMODE=require` is set.
- Your network permits outbound PostgreSQL connections.

## 5. Apply Migrations

```powershell
cd emotion_dashboard
..\.venv\Scripts\python.exe manage.py showmigrations monitor
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py migrate
cd ..
```

Back up an existing production database before applying new migrations.

## 6. Create the Platform Administrator

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py createsuperuser
```

## 7. Create the Tenant

Start Django, sign into `/admin/`, then create:

1. A bank with a globally unique uppercase code.
2. One or more active branches with unique bank-local codes and PC prefixes.
3. A bank administrator by assigning the bank and leaving branch empty.
4. Optional branch users by assigning a specific branch.

## 8. Create the Bank Upload Key

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py set_bank_api_key YOUR_BANK_CODE
```

The raw key is displayed once. Copy it to `BANK_API_KEY` on every authorized teller computer for that bank.

---

# Running the System

Open three PowerShell terminals in the repository root.

## Terminal 1: Django Dashboard

```powershell
.\.venv\Scripts\Activate.ps1
cd emotion_dashboard
python manage.py runserver 8000
```

Open:

```text
http://127.0.0.1:8000/
```

## Terminal 2: FastAPI

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

Verify:

```text
http://127.0.0.1:8001/health
```

The first processed upload may take longer while DeepFace loads models.

## Terminal 3: Production Capture Client

```powershell
.\.venv\Scripts\Activate.ps1
python desktop_capture.py
```

Run only one camera client at a time. In preview mode, press `Q` or `Esc` to exit.

The workstation's Windows name must begin with an active PC prefix belonging to the configured `BANK_CODE`.

## Reference Client

For basic integration testing only:

```powershell
.\.venv\Scripts\python.exe clients\device_agent.py
```

## Stop the System

Use `Ctrl+C` in the Django and FastAPI terminals. Stop the capture window with `Q` or `Esc`, or interrupt its terminal with `Ctrl+C`.

A stopped API or dashboard does not automatically stop the other process. The capture client queues retryable uploads while the API is unavailable, subject to its configured queue limit.

---

# OpenCV Troubleshooting

If the client reports that `cv2` has no `CascadeClassifier`, verify the active interpreter:

```powershell
.\.venv\Scripts\python.exe -c "import cv2; print(cv2.__file__); print(cv2.__version__); print(hasattr(cv2, 'CascadeClassifier'))"
```

Stop all running Python processes using OpenCV, then reinstall the pinned dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip uninstall -y opencv-python opencv-python-headless
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Do not run Uvicorn with the global Python installation while using packages installed only in `.venv`.

---

# Docker Compose

Docker Compose runs the dashboard and API against the configured hosted Supabase database:

```powershell
docker compose up --build
```

Compose:

- Loads application configuration from `.env`.
- Publishes Django on port `8000`.
- Publishes FastAPI on port `8001`.
- Shares a private `captured_faces` volume between both services.
- Does not create, replace, or migrate a local database automatically.

Apply migrations deliberately before serving production traffic.

Stop the containers without deleting stored image data:

```powershell
docker compose down
```

Removing the named volume deletes the Compose-managed captured images. Do not remove it without a verified backup and retention authorization.

---

# Legacy Jupyter Notebooks

The notebooks under `research/legacy_notebooks/` are retained for supervised research and migration reference. They are not the supported SaaS capture or processing path.

```text
desktop_capture.ipynb   supervised capture experiment
main.ipynb              sample-image expression exploration
process-faces.ipynb     legacy database batch experiment
prototype.ipynb         legacy live-preview prototype
```

The notebooks may refer to older schemas or local database assumptions. Do not run their write cells against the shared Supabase production database without reviewing every query.

Use the root `desktop_capture.py` and FastAPI service for the maintained runtime.

---

# Database Architecture

## Shared SaaS Database

Every tenant uses the same logical schema, with tenant ownership enforced through bank foreign keys and server-side filters.

```text
tenant_bank
      |
      +---- tenant_branch
      +---- tenant_bank_settings
      +---- monitor_customuser
      +---- analytics_visitor
      `---- analytics_snapshot
```

The application relies on relational tenant keys, model validation, scoped Django query helpers, and bank-scoped API SQL. Database access must never omit the bank boundary.

## Connection Configuration

Django uses persistent connections with health checks. FastAPI creates PostgreSQL connections using the same environment values and a bounded connection timeout.

The default `DB_CONN_MAX_AGE=60` is suitable as a starting point for the Session pooler. Tune connection lifetime and capacity using Supabase plan limits and observed traffic.

## SQLite

SQLite is supported only for isolated Django CI tests through `DATABASE_URL=sqlite:...`. The SaaS runtime and ingestion API require PostgreSQL.

---

# Migrations

Current monitor migrations:

```text
0001_initial
0002_bank_api_key_rotated_at_alter_bank_code_and_more
```

Before committing model changes:

```powershell
cd emotion_dashboard
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test monitor -v 2
```

When a schema change is intentional:

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations monitor
..\.venv\Scripts\python.exe manage.py migrate
```

Review generated migrations. Test both forward migration and backup restoration before production deployment.

---

# Security and Privacy Requirements

## Tenant Isolation

- Every dashboard query must start from a tenant-aware helper or equivalent explicit scope.
- Private image lookup must use the same visible snapshot scope.
- Face matching must query embeddings from the authenticated bank only.
- Branch resolution must remain inside the authenticated bank.
- Exports must never bypass the current user's scope.

## Upload Security

- Keep bank keys unique, long, private, and rotated.
- Store raw teller credentials in an OS-appropriate secret location.
- Reject invalid content types, oversized payloads, invalid images, and unsafe paths.
- Apply reverse-proxy request limits and rate limits in production.
- Do not expose FastAPI directly to an untrusted network without HTTPS and edge controls.

## Image and Biometric Privacy

- Obtain legal and privacy review for every deployment jurisdiction.
- Provide clear notice and obtain consent where required.
- Treat face images and embeddings as sensitive biometric data.
- Collect only the customer capture region needed for the stated purpose.
- Define retention, deletion, access, export, and incident-response processes.
- Restrict production files to private encrypted storage.
- Log sensitive-data access without logging raw credentials or embeddings.

## Expression-Model Safety

- Describe results as facial-expression estimates, not verified emotions.
- Prefer aggregate service-quality analytics over individual evaluation.
- Validate error rates across relevant lighting, cameras, skin tones, ages, glasses, head poses, and accessibility needs.
- Do not infer intent, honesty, satisfaction, or risk from one classification.
- Require human review for any operational interpretation.

## Secrets

Never commit or send in screenshots:

```text
.env
Supabase passwords
DJANGO_SECRET_KEY
bank upload keys
captured images
face embeddings
offline queue contents
production exports
```

Rotate any credential that has been exposed in chat, terminal logs, screenshots, or source history.

---

# Production Security Configuration

Minimum Django production values:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=use-a-secret-manager-generated-value
DJANGO_ALLOWED_HOSTS=dashboard.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dashboard.example.com
DJANGO_SECURE_SSL_REDIRECT=True
EMAIL_BACKEND=your.production.EmailBackend
```

Also configure:

- HTTPS termination with correct forwarded-protocol headers.
- Restricted network paths to Supabase.
- A secret manager instead of a checked-in environment file.
- Secure SMTP or another supported password-reset delivery service.
- Reverse-proxy body-size and request-rate limits.
- Centralized structured logs, metrics, uptime checks, and alerts.
- Private object storage before scaling web processes across hosts.
- Backup, recovery, retention, and deletion automation.
- Dependency and container vulnerability scanning.

Run:

```powershell
cd emotion_dashboard
..\.venv\Scripts\python.exe manage.py check --deploy
```

Resolve every relevant warning before release.

---

# Testing

## API, Configuration, and Camera Tests

From the repository root:

```powershell
$env:DATABASE_URL = 'postgresql://unused:unused@localhost/unused'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:DATABASE_URL
```

These tests mock database operations and do not require the hosted Supabase database.

## Django Tenant Tests

Run from the repository root:

```powershell
Push-Location emotion_dashboard
$testDb = (Join-Path (Get-Location) 'test-dashboard.sqlite3').Replace('\', '/')
$env:DJANGO_DEBUG = 'true'
$env:DJANGO_SECRET_KEY = 'test-only'
$env:DATABASE_URL = "sqlite:///$testDb"
..\.venv\Scripts\python.exe manage.py test monitor -v 2
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:DJANGO_SECRET_KEY -ErrorAction SilentlyContinue
Remove-Item Env:DJANGO_DEBUG -ErrorAction SilentlyContinue
Pop-Location
```

Delete the temporary SQLite file after the test process releases it if it remains.

## Compilation and Migration Checks

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m compileall -q api_server clients emotion_dashboard tests desktop_capture.py
Push-Location emotion_dashboard
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
Pop-Location
```

## Continuous Integration

`.github/workflows/ci.yml` runs:

- Python 3.10 dependency installation.
- Source compilation.
- API, configuration, and camera unit tests.
- Django migration checks and tenant tests on isolated SQLite.
- Django's production deployment check.

CI must not receive or contact the production Supabase database.

---

# Recommended Test Expansion

Prioritize automated coverage for:

- Cross-bank authorization attempts on every dashboard and image route.
- Bank-admin versus branch-user settings permissions.
- API-key rotation and immediate invalidation.
- Longest-prefix branch matching edge cases.
- Concurrent uploads for the same new visitor.
- Invalid, malformed, oversized, and decompression-heavy images.
- Model timeout and capacity saturation handling.
- Offline queue bounds, retry order, and terminal rejection behavior.
- Private object-storage adapters.
- Retention deletion with legal holds and audit evidence.
- Dashboard aggregation correctness across time zones.
- Bias, calibration, and expression-quality evaluation datasets.

---

# Known Implementation Gaps

## 1. Billing and Subscriptions

The data model supports multiple banks, but it does not yet implement plans, subscriptions, metering, invoices, payment-provider webhooks, quotas, or entitlement enforcement.

## 2. Self-Service Tenant Onboarding

Platform administrators currently create tenants, users, branches, and initial credentials. There is no complete self-service signup, verification, trial, or organization-invitation flow.

## 3. Private Storage Is Single-Host

The default local/Compose file volume is unsuitable for horizontally scaled API and dashboard hosts. Production needs shared private object storage with signed or authorized delivery.

## 4. Retention Is Configured but Not Automated

Bank retention preferences exist, but a scheduled deletion service, deletion audit trail, recovery window, and legal-hold process are not yet implemented.

## 5. Notification Delivery Is Not Implemented

Users can store weekly-summary and negative-expression preferences, but no scheduler sends those notifications yet.

## 6. Expression Accuracy Requires Validation

DeepFace defaults and global thresholds have not been proven accurate for every target branch environment. Camera and model calibration remain deployment requirements.

## 7. No Liveness or Anti-Spoofing

Persistent face matching can be fooled by presentation attacks. Add and validate liveness controls before relying on identity continuity in a security-sensitive workflow.

## 8. No Packaged Teller Application

The production camera client is currently a Python process rather than a signed Windows installer/service with managed upgrades, status controls, and enterprise deployment policy.

## 9. Synchronous ML Limits Throughput

Face analysis occurs in the API process. Capacity is deliberately bounded, but larger deployments will need measured scaling or an asynchronous inference architecture.

## 10. Commercial Observability Is Incomplete

Central logs, tenant-aware metrics, traces, alerts, audit logs, incident workflows, and formal service-level objectives remain to be built.

---

# Performance Considerations

## Database

The schema includes indexes for common bank, branch, visitor, and timestamp filters. Keep every analytics query tenant-scoped before applying dates, pagination, or aggregation.

Use the Supabase Session pooler and monitor connection consumption. Avoid creating a new unbounded pool per web worker.

## Face Matching

`MAX_EMBEDDING_CANDIDATES` bounds database candidates, but comparison still grows with the number of stored tenant embeddings. At larger scale, evaluate PostgreSQL vector indexing or a tenant-partitioned vector service.

## Inference

DeepFace models are memory-intensive and first-use loading is slow. Measure:

```text
model warm-up time
processing latency percentiles
memory per API worker
CPU/GPU utilization
rejection rates by quality gate
concurrent-capacity saturation
```

Do not multiply Uvicorn workers without accounting for one model copy per process.

## Images

Use bounded uploads, private lifecycle policies, and thumbnails where appropriate. Avoid loading full-resolution images into dashboard list views.

---

# Deployment Architecture

A production-ready direction is:

```text
Teller workstations
        |
        | HTTPS
        v
WAF / reverse proxy / rate limiter
        |
        +---- FastAPI ingestion instances
        |          |
        |          +---- private object storage
        |          `---- Supabase Session pooler
        |
        `---- Django dashboard instances
                   |
                   +---- private object storage
                   `---- Supabase Session pooler
                              |
                              v
                    Supabase PostgreSQL
```

Keep the dashboard and ingestion surfaces separately routable so upload traffic cannot starve interactive users.

---

# Production Deployment Checklist

Before a real bank deployment:

- [ ] Complete privacy, biometric-data, consent, and legal review.
- [ ] Rotate every development or exposed credential.
- [ ] Store secrets in the hosting platform's secret manager.
- [ ] Configure HTTPS-only dashboard and API domains.
- [ ] Configure allowed hosts and trusted CSRF origins.
- [ ] Configure a production email backend.
- [ ] Run `manage.py check --deploy`.
- [ ] Back up Supabase and test restoration.
- [ ] Move captures to private encrypted object storage.
- [ ] Implement automated retention and deletion.
- [ ] Add API rate limits and request-size limits.
- [ ] Add liveness controls if persistent matching remains enabled.
- [ ] Calibrate each camera and customer ROI.
- [ ] Validate model performance on representative consenting participants.
- [ ] Package and sign the teller application.
- [ ] Add centralized logs, metrics, alerts, and audit trails.
- [ ] Define incident response, rollback, and disaster recovery.
- [ ] Load-test concurrent uploads and dashboard queries.
- [ ] Document tenant onboarding, suspension, and deletion.
- [ ] Add billing and entitlement enforcement before public SaaS sales.

---

# Backup and Restore

Backups must cover both:

1. Supabase PostgreSQL records.
2. Private captured images stored outside PostgreSQL.

A database restore without the matching image objects leaves broken evidence links. An image restore without matching database rows leaves orphaned sensitive files.

Define:

```text
backup frequency
retention duration
encryption and key ownership
restore-time objective
restore-point objective
tenant deletion propagation
regional storage requirements
restore exercise schedule
```

Test restoration in an isolated environment. Never restore production biometric data into an unsecured developer workspace.

---

# Logging and Monitoring

Production telemetry should include:

- Django and FastAPI request rate, latency, and error rate.
- Supabase connection failures and pool saturation.
- Upload rejections by reason without storing image contents in logs.
- Processing latency and ML capacity timeouts.
- Teller queue depth and last successful upload.
- Branch offline status.
- Storage growth and retention-task results.
- Authentication failures and API-key rotations.
- Cross-tenant authorization denials.

Never log raw upload keys, database passwords, face embeddings, or image bytes.

---

# Git Ignore

Keep runtime and secret material excluded from Git. Add any environment- or tool-specific directories to `.gitignore` when they are created:

```gitignore
.env
.venv/
.venv-*/
__pycache__/
*.pyc
captured_faces/
offline_queue/
queued_captures/
*.sqlite3
.ipynb_checkpoints/
```

Before committing:

```powershell
git status --short
git diff --check
```

If thousands of files appear, confirm virtual-environment directories are ignored and were never staged.

---

# Coding Standards

## Django

- Start tenant data access from a scoped queryset.
- Keep authorization checks in server-side code.
- Use migrations for schema changes.
- Preserve model validation for tenant relationships.
- Stream large exports instead of building them fully in memory.

## FastAPI

- Authenticate the bank before branch lookup or face matching.
- Return safe client messages and keep detailed exceptions in protected logs.
- Bound upload bytes, processing concurrency, database candidates, and timeouts.
- Roll back all database work on processing failure.
- Remove newly stored images when a request fails.

## Camera Client

- Never block the camera loop on a slow network request.
- Keep retry queues bounded and private.
- Calibrate quality thresholds rather than disabling them casually.
- Avoid capturing outside the intended customer area.
- Provide a clear stop mechanism and deployment notice.

## Database

- Include `bank_id` in every tenant-owned query.
- Prefer transactions for related visitor and snapshot writes.
- Review indexes with real query plans before adding or removing them.
- Never test destructive migrations against production first.

## Secrets

- Use environment variables or a secret manager.
- Use examples and placeholders in documentation.
- Rotate exposed values rather than merely deleting them from the latest commit.

---

# Git Workflow

The branch boundary is deliberate:

```text
main        hosted, multi-bank, Supabase SaaS
non-saas    local, single-installation product
```

Recommended feature workflow:

```powershell
git switch main
git pull --ff-only
git switch -c feature/short-description
```

Before opening a pull request:

```powershell
git status --short
git diff --check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd emotion_dashboard
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test monitor -v 2
```

When porting a fix from `non-saas`, inspect and apply the smallest relevant change. Do not merge the entire branch into `main`.

---

# Pull Request Requirements

Every pull request should state:

- What changed and why.
- Which tenant roles and routes are affected.
- Whether database schema or migration state changed.
- Whether environment variables changed.
- Whether upload, image, embedding, or retention behavior changed.
- Which automated tests were run.
- Which manual camera or browser checks were run.
- Any privacy, security, model-risk, or deployment implications.
- Screenshots for meaningful UI changes using non-sensitive data.

A reviewer should explicitly check tenant isolation for any queryset, raw SQL, export, image, or API modification.

---

# Current Implementation Scope

## Implemented

- Multi-bank tenant, branch, and user data model.
- Platform, bank-admin, and branch-user authorization.
- Supabase PostgreSQL configuration shared by Django and FastAPI.
- TLS-enabled database connections.
- Hashed bank upload keys with rotation.
- PC-prefix branch assignment within the authenticated bank.
- Bounded authenticated image ingestion.
- Synchronous DeepFace extraction, embedding, matching, and expression analysis.
- Tenant-scoped visitor identity and snapshot persistence.
- Private authenticated image delivery.
- Dashboard, branch comparison, analytics, visitors, history, and reports.
- User, bank, branch, and dashboard settings.
- Production-oriented camera selection and retry workflow.
- Docker development configuration.
- Automated unit, tenant, migration, and deployment checks.

---

# Not Production-Complete

The repository should not yet be represented as a finished commercial SaaS platform because it lacks:

- Billing, plans, subscriptions, metering, quotas, and entitlements.
- Self-service tenant onboarding and lifecycle management.
- Production private object storage.
- Automated retention and deletion execution.
- Complete audit logging and compliance evidence.
- Liveness and anti-spoofing controls.
- Formal model validation and monitoring.
- Signed, managed teller desktop distribution.
- Centralized observability and service-level objectives.
- Regularly exercised disaster recovery.

---

# Development Priorities

## P0 — Privacy, Isolation, and Safety

1. Complete legal/privacy review and consent design.
2. Add automated cross-tenant security tests for every data surface.
3. Move captures to private encrypted object storage.
4. Implement retention, deletion, and audit workflows.
5. Validate expression performance and add liveness where required.

## P1 — SaaS Product Foundations

1. Add plans, subscriptions, billing-provider integration, and entitlements.
2. Add secure tenant signup, invitations, and lifecycle management.
3. Add tenant quotas for branches, users, uploads, storage, and retention.
4. Add platform audit logs and support tooling.

## P2 — Operational Reliability

1. Add centralized logs, metrics, traces, and alerts.
2. Package, sign, monitor, and remotely update the teller application.
3. Add automated deployment, rollback, backups, and restore exercises.
4. Load-test ingestion, matching, analytics, and exports.

## P3 — Model and Analytics Quality

1. Create representative consented evaluation datasets.
2. Track uncertain classifications and per-site quality metrics.
3. Evaluate multi-frame expression consensus.
4. Improve aggregate reporting without encouraging individual high-impact use.

---

# Definition of Done

A change is complete when:

- [ ] Tenant isolation remains correct for platform, bank, and branch roles.
- [ ] Relevant tests pass.
- [ ] Migration state is clean.
- [ ] Failure paths do not leave partial database rows or orphaned files.
- [ ] New settings are documented in `.env.example` and this README.
- [ ] Secrets and sensitive data are absent from the diff.
- [ ] Privacy and model-risk effects have been considered.
- [ ] Local and production behavior are distinguished.
- [ ] Documentation matches the implemented code.

---

# Collaborator Checklist

## Before Development

- Confirm you are on `main` for SaaS work.
- Pull with `--ff-only` and create a focused feature branch.
- Read [Architecture](docs/architecture.md), [Security](docs/SECURITY.md), and [Deployment](docs/DEPLOYMENT.md).
- Copy `.env.example` without overwriting an existing `.env`.
- Use test tenant data and consenting participants only.

## Before Review

- Run unit, Django, migration, and deployment checks.
- Inspect `git status --short` for generated files and environments.
- Run `git diff --check`.
- Verify every new data path is tenant-scoped.
- Update documentation and example configuration.
- Remove screenshots, exports, captures, and logs containing sensitive data.

---

# Reporting Technical Issues

Include:

```text
branch and commit
operating system and Python version
exact command
full traceback with secrets removed
affected component
expected and actual behavior
whether Supabase health succeeds
whether the issue affects one tenant or all tenants
reproduction steps using non-sensitive data
```

For camera issues, also include the OpenCV version, camera model, configured resolution, and whether another application is using the camera.

For model-quality issues, describe lighting, pose, crop quality, blur, confidence vector, and multiple repeated samples. Do not submit identifiable customer images in a public issue.

---

# Project Status

The SaaS core is functional for controlled development and pilot evaluation:

```text
Tenant model and authorization       Implemented
Supabase-backed dashboard            Implemented
Authenticated capture ingestion      Implemented
Face matching and expression signal  Implemented
Private single-host image access     Implemented
Commercial billing and onboarding    Not implemented
Multi-host private object storage    Not implemented
Formal production validation         Required
```

Use in a real banking environment requires privacy approval, security hardening, model validation, operational controls, and commercial platform work.

---

# Documentation Rule

When code and documentation disagree, treat the implementation and automated tests as the current behavior, then update the documentation in the same change.

Related documents:

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Security](docs/SECURITY.md)
- [Development usage](docs/usage.md)
- [Contributing](docs/contributing.md)
- [Migration guide](docs/MIGRATION_GUIDE.md)
- [Desktop capture developer guide](DESKTOP_CAPTURE_EMOTION_DETECTION_README.md)

---

# License

This project is licensed under the [MIT License](LICENSE).

The license does not replace legal, privacy, biometric-data, regulatory, security, or model-validation obligations for a deployment.

---

<p align="center">
  Built for tenant-isolated, privacy-conscious customer-service analytics.
</p>
