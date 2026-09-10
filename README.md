# Smart Customer Sentiment Analysis

> A self-hosted, branch-aware facial-expression analytics platform with silent desktop capture, authenticated ingestion, background inference, privacy controls, reporting, and operational dashboards.

![Django](https://img.shields.io/badge/Django-5.2.11-092E20?style=flat-square&logo=django&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Ingestion_API-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10.x-3776AB?style=flat-square&logo=python&logoColor=white)
![MariaDB](https://img.shields.io/badge/XAMPP-MariaDB-FB7A24?style=flat-square&logo=mariadb&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![DeepFace](https://img.shields.io/badge/DeepFace-0.0.98-6C5CE7?style=flat-square)
![Deployment](https://img.shields.io/badge/Deployment-Self--Hosted-34495E?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active_Development-orange?style=flat-square)

---

# Overview

**Smart Customer Sentiment Analysis**, presented in the interface as **Sentiment Grid**, is a non-SaaS application for one organization to operate on its own infrastructure.

The system combines:

1. Silent desktop camera capture
2. Per-device API authentication
3. Image validation and rate limiting
4. Redis-backed background processing
5. Face-quality filtering
6. RetinaFace detection and alignment
7. DeepFace facial-expression classification
8. Multi-frame confidence smoothing
9. Branch-scoped dashboard access
10. Emotion trends and branch comparisons
11. CSV reporting
12. Privacy-focused image retention controls

The application is split into a Django dashboard, a FastAPI ingestion service, an RQ inference worker, a Redis queue, and a Windows camera agent. All persistent application data is stored in the same XAMPP MySQL/MariaDB database.

The main runtime path is:

```text
Customer-facing camera
         |
         v
Silent desktop agent
         |
         | Cropped face + device API key
         v
FastAPI ingestion service
         |
         +----> XAMPP MariaDB: queued snapshot
         |
         +----> Private image storage
         |
         v
Redis / RQ queue
         |
         v
DeepFace worker
         |
         +----> Quality checks
         +----> RetinaFace alignment
         +----> Expression inference
         +----> Burst consensus
         |
         v
XAMPP MariaDB: processed result
         |
         v
Django dashboard and reports
```

The dashboard is server-rendered with Django templates, HTML, CSS, JavaScript, Bootstrap icons, and Chart.js.

> **Interpretation boundary**
>
> The model classifies visible facial-expression patterns. It does not prove a person's internal emotional state, intent, honesty, creditworthiness, or risk. Results must not be used for credit, fraud, eligibility, security, employment, or other decisions about an individual.

---

# Non-SaaS Deployment Model

One installation belongs to one organization.

The `non-saas` branch intentionally has no:

```text
Customer tenants
Organizations table
Subscription plans
Billing accounts
Monthly usage quotas
Commercial feature gates
Tenant selector
```

Physical branches remain part of the design because they provide operational grouping, user access boundaries, and comparison reporting.

Device keys, authenticated dashboard accounts, upload limits, rate limits, and privacy controls are security features and remain enabled.

> **Branch rule**
>
> `non-saas` and `main` represent different product editions. Do not merge either branch wholesale into the other. Move an individual fix between editions only after reviewing its database, configuration, tenancy, and UI impact.

---

# Architecture

## Architectural Style

The system uses separate processes with a shared relational database:

```text
+----------------------+       +-------------------------+
| Windows camera PC    |       | Authorized web browser  |
|                      |       |                         |
| Silent camera agent  |       | Django dashboard        |
+----------+-----------+       +------------+------------+
           |                                |
           | HTTP multipart upload          | HTTP session
           v                                v
+---------------------------------------------------------+
|                    Application host                     |
|                                                         |
|  FastAPI ingestion     Redis/RQ      DeepFace worker    |
|          |                 |                 |           |
|          +---------------->+---------------->+           |
|          |                                   |           |
|          +----------- Private uploads -------+           |
+-----------------------------+---------------------------+
                              |
                              v
                  +------------------------+
                  | XAMPP MySQL / MariaDB  |
                  | Jobs, users, results   |
                  +------------------------+
```

## Ownership Boundaries

- Django migrations own the relational schema.
- Django owns user authentication, authorization, dashboards, settings, reports, and administration.
- FastAPI owns authenticated image ingestion and job submission.
- Redis carries transient RQ jobs and rate-limit counters.
- The worker owns image-quality checks, model inference, temporal smoothing, and result persistence.
- The desktop agent owns camera acquisition, finite pause controls, local retry storage, and upload retries.
- XAMPP MySQL/MariaDB stores all durable application records.
- Private upload storage is shared by the API and worker on a single host.

---

# Runtime Components

## Django Dashboard

The dashboard provides:

```text
Dashboard overview
Branch comparison
Branch detail analytics
Emotion analytics
Reports and CSV export
User preferences
Branch settings for administrators
Device health information
Django administration
```

The visual design keeps the dark Sentiment Grid interface used by the SaaS edition while the data and tenancy model remain self-hosted and non-SaaS.

## FastAPI Ingestion Service

The ingestion service:

- Authenticates each camera using `X-API-Key`.
- Rejects inactive devices and inactive branches.
- Validates MIME type, actual image format, dimensions, and byte size.
- Applies a per-device Redis rate limit.
- Normalizes accepted uploads to JPEG.
- Writes a queued snapshot record to MariaDB.
- Enqueues inference work in Redis/RQ.
- Exposes health and device-scoped job-status endpoints.
- Does not import TensorFlow or run DeepFace.

## DeepFace Worker

The long-lived worker:

- Loads the expression model once and keeps it warm.
- Uses RetinaFace for detection and facial alignment by default.
- Rejects images that are too small, blurry, too dark, or overexposed.
- Classifies the seven DeepFace expression categories.
- Combines up to three captures from the same short device session window.
- Stores `uncertain` instead of forcing a weak or closely split label.
- Supports optional installation-wide ArcFace identity matching.
- Deletes processed and rejected raw images when retention is disabled.

## Silent Desktop Camera Agent

The Windows agent:

- Has no live camera preview.
- Opens the camera for a bounded capture window.
- Captures up to three images per acquisition by default.
- Releases the camera before face processing or network upload.
- Backs off when another application owns the camera.
- Queues failed uploads locally within a configured limit.
- Provides finite pause controls through a notification-area icon.
- Automatically resumes when a pause lease expires.
- Persists pause expiry across agent and computer restarts.

## Redis

Redis provides:

```text
RQ face-processing queue
Per-device upload counters
Transient job coordination
```

Redis is not the system of record. MariaDB remains authoritative for snapshot state and results.

## XAMPP MySQL / MariaDB

The local database stores:

```text
Branches
Dashboard users
User preferences
Registered devices
Device key hashes
Visitor/session identities
Snapshot jobs
Expression vectors
Confidence values
Optional embeddings
Processing status and errors
```

---

# Access and Authorization Model

## System Administrators

Django superusers can:

```text
View all active branches
Compare branches
Manage branch settings
View all permitted snapshots and visitors
Register, disable, and review devices in Django admin
Create device API keys
Manage users and branch assignments
```

## Branch Users

Normal authenticated users:

- Must be assigned to an active branch.
- Can view only their assigned branch, snapshots, visitors, devices, and reports.
- Cannot access installation-wide branch comparison operations.
- Cannot change another branch's settings.

Conceptually:

```text
Authenticated user
        |
        +---- Superuser ----> All active branches
        |
        +---- Normal user --> Assigned active branch only
        |
        +---- No assignment -> No branch data
```

Authorization is enforced in server-side query helpers in `emotion_dashboard/monitor/access.py`; hiding a link in the UI is not treated as access control.

## Device Access

Every camera device belongs to one branch and has:

```text
Unique PC name
Unique API-key prefix
SHA-256 API-key hash
Active/inactive state
Created timestamp
Last-seen timestamp
```

The full device key is displayed only once when created. Disable the `Device` record in Django admin to revoke it.

---

# Authentication

Current routes:

```text
/                  Application login
/login/            Django login compatibility route
/logout/           POST-only logout
/password-reset/   Password reset request
/reset/.../         Password reset confirmation
/admin/             Django administration
```

Django password validators, HTTP-only cookies, CSRF protection, clickjacking protection, content-type sniffing protection, and same-origin referrer policy are enabled.

When `DJANGO_DEBUG=false`, the application also enables secure cookies, HTTPS redirection, HSTS, and proxy SSL-header support.

---

# Core Data Model

## Branch

Important fields:

```text
name
pc_prefix
location
is_active
```

`pc_prefix` is globally unique within the installation.

## CustomUser

The project uses a custom Django user model with an optional protected branch assignment.

```text
CustomUser
    |
    +---- Superuser: installation-wide access
    |
    +---- Normal user: assigned branch access
```

## UserPreference

Per-user settings include:

```text
Default date range
Default hourly range
Default branch
Automatic refresh interval
Compact mode
Reduced motion
Weekly-summary preference
Negative-expression notification preference
Notification threshold
Minimum detection count
```

Notification preferences are stored, but automated email/alert delivery is not yet implemented as a production background service.

## Device

`Device` connects one authenticated capture computer to one branch. Device keys are stored as hashes rather than plaintext.

## Visitor

`Visitor` stores a generated identity string and first/last-seen timestamps.

With face identification disabled, visitor identity is scoped to the short-lived device session:

```text
session-<device_id>-<session_id>
```

With face identification enabled, the worker can compare ArcFace embeddings across the installation.

## CapturedSnapshot

Important fields:

```text
job_id
branch
device
visitor
pc_name
session_id
image_path
upload_content_type
upload_size_bytes
timestamp
status
emotion
confidence
emotion_vector
processed
embedding
error_message
processed_at
```

Snapshot states are:

```text
queued -> processing -> processed
                    |
                    +-> failed
```

Poor-quality frames are terminally rejected and recorded as failed with `PoorImageQuality` so they do not pollute dashboard analytics.

---

# Capture and Analysis Pipeline

## Camera Acquisition

For each sampling cycle, the desktop agent:

```text
Check finite pause lease
        |
        v
Wait for capture interval
        |
        v
Open camera
        |
        +---- Camera unavailable -> Release and retry later
        |
        v
Warm camera frames
        |
        v
Capture bounded image burst
        |
        v
Release camera
        |
        v
Detect and crop largest face
        |
        v
Upload or queue locally
```

The default timing is:

```text
Capture cycle interval       10 seconds
Maximum open window           2 seconds
Images per open window        3
Burst image spacing        0.75 seconds
Camera-busy retry             15 seconds
```

## Ingestion Validation

Accepted upload formats:

```text
JPEG
PNG
WebP
```

The API checks:

```text
Device authentication
Device and branch active state
Declared MIME type
Decoded image format
Non-empty body
Maximum byte size
Minimum dimensions
Maximum pixel count
Session-ID format
Per-device request rate
```

## Image Quality Gate

Before inference, the worker checks:

```text
Minimum face dimensions
Laplacian sharpness
Minimum brightness
Maximum brightness
Successful image decoding
Successful face detection
```

The thresholds are configurable through `EMOTION_*` environment variables and should be calibrated using consented images from the real camera position.

## Expression Classification

The DeepFace model emits these raw categories:

```text
angry
disgust
fear
happy
sad
surprise
neutral
```

The worker normalizes the probability vector before saving it.

## Multi-Frame Consensus

The agent uploads several images with the same session ID. The worker queries recent processed vectors from that device session and averages them over a short window.

```text
Frame 1 probabilities --+
                       |
Frame 2 probabilities --+--> Normalized mean --> Confidence rules --> Result
                       |
Frame 3 probabilities --+
```

By default, the final result becomes `uncertain` when:

```text
Fewer than 2 usable samples exist
Top probability is below 55%
Top-two probability margin is below 10 percentage points
```

This prevents a borderline result from being presented as a reliable label. For example, a 49% `sad` result is no longer treated as confidently sad.

## Optional Face Identification

Face identification is disabled by default:

```dotenv
ENABLE_FACE_IDENTIFICATION=false
```

When explicitly enabled, the worker builds ArcFace embeddings and compares them with the nearest stored embedding using cosine distance and `MATCH_THRESHOLD`.

This feature materially changes the privacy profile of the installation. Do not enable it without a documented purpose, access restrictions, retention rules, and legal/privacy review.

---

# Dashboard and Analytics

## Dashboard Overview

The main dashboard provides:

```text
Today's visitors
Top expression
Negative-expression rate
Current activity
Expression distribution
Time-series trends
Hourly activity
Branch filters
Date-range filters
```

## Branch Comparison

Installation administrators can compare active branches by:

```text
Visitor volume
Top expression
Positivity score
Net expression trend
Selected time period
```

## Branch Detail

Branch detail includes:

```text
Total detections
Tracked expressions
Expression distribution
Hourly visit activity
Hourly positivity
Recent captures
Normalized confidence percentages
```

Raw-image links return 404 after deletion when `DELETE_RAW_IMAGE_AFTER_PROCESSING=true`. This is expected and preserves the default privacy policy.

## Reports

The reporting interface supports branch-aware filters and CSV export. Exported data may include identifiers, branch names, device names, expression labels, confidence values, and timestamps. Treat exports as sensitive operational data.

---

# Ingestion API

Local base URL:

```text
http://127.0.0.1:8001
```

## Authentication Header

```http
X-API-Key: scs_<prefix>_<secret>
```

## `GET /`

Returns basic service status.

## `GET /health`

Checks MariaDB and Redis. Returns HTTP 503 when either dependency is unavailable.

## `POST /v1/snapshots`

Uploads one cropped face using `multipart/form-data`:

```text
file        Required image file
session_id  Optional 8-64 character session identifier
```

Successful response:

```json
{
  "job_id": "01J...",
  "status": "queued"
}
```

The compatibility route `POST /upload-face` maps to the same handler.

## `GET /v1/snapshots/{job_id}`

Returns a job only when it belongs to the authenticated device.

## `GET /v1/snapshots/{job_id}/image`

This authenticated development endpoint is disabled unless:

```dotenv
ENABLE_DEV_IMAGE_ENDPOINT=true
```

Keep it disabled outside controlled local development.

---

# Technology Stack

| Layer | Technology |
|---|---|
| Dashboard | Django 5.2.11 |
| Ingestion API | FastAPI and Uvicorn |
| Background jobs | Redis 7 and RQ 2.x |
| Expression inference | DeepFace 0.0.98 and TensorFlow 2.13 |
| Face detection | RetinaFace |
| Optional identity model | ArcFace |
| Image processing | OpenCV 4.11 and Pillow |
| Database | XAMPP MySQL/MariaDB with `mysqlclient` |
| Frontend | Django templates, Bootstrap icons, Chart.js, custom CSS/JavaScript |
| Desktop integration | OpenCV, Requests, Pystray, Pillow |
| Containers | Docker Compose |
| CI | GitHub Actions |

Python 3.10 is required for the pinned TensorFlow worker environment.

---

# Repository Structure

```text
Smart-Customer-Sentiment-Analysis-fixed/
|
+-- api_server/
|   +-- api/index.py                  Serverless API adapter
|   +-- config.py                     API and worker configuration
|   +-- db_utils.py                   MariaDB data-access layer
|   +-- face_api.py                   FastAPI ingestion service
|   +-- face_utils.py                 Matching and image helpers
|   +-- security.py                   Device-key helpers
|   +-- worker.py                     Inference and consensus logic
|   +-- worker_main.py                Long-lived RQ worker entry point
|   +-- requirements.txt              API dependencies
|   +-- requirements-worker.txt       TensorFlow/DeepFace dependencies
|
+-- clients/
|   +-- device_agent.py               Silent Windows camera agent
|
+-- emotion_dashboard/
|   +-- emotion_dashboard/            Django project settings and URLs
|   +-- monitor/                      Models, views, access, UI, migrations
|   +-- manage.py
|   +-- requirements.txt
|
+-- research/
|   +-- legacy_notebooks/             Supervised legacy experiments
|   +-- README.md
|
+-- tests/                             API, worker, camera, config tests
+-- docs/                              Architecture, API, security, deployment
+-- .github/workflows/ci.yml           Continuous integration
+-- .env.example                       Safe configuration template
+-- docker-compose.yml                 Redis and application services
+-- Dockerfile.api
+-- Dockerfile.dashboard
+-- Dockerfile.worker
+-- requirements.txt                   Shared local development dependencies
+-- requirements-notebook.txt          Optional notebook environment
+-- LICENSE                            MIT license
+-- README.md
```

---

# Application Routes

## Dashboard

```text
/dashboard/                 Dashboard overview
/branches/                  Branch comparison
/branch/<id>/               Branch detail
/emotion-analytics/         Expression analytics
/reports/                   Reports and exports
/settings/                  Profile and dashboard settings
/snapshot/<id>/image/       Authorized retained-image endpoint
```

## Administration

```text
/admin/                     Django administration
```

## API

```text
:8001/                      API service status
:8001/health                Dependency health
:8001/v1/snapshots          Snapshot ingestion
:8001/v1/snapshots/<job>    Device-scoped job status
```

---

# Environment Configuration

Copy `.env.example` to `.env`. Never commit the populated `.env` file.

## Database

```dotenv
DATABASE_ENGINE=mysql
MYSQL_DATABASE=smart_sentiment
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
DB_CONN_MAX_AGE=0
XAMPP_ALLOW_MARIADB_10_4=true
```

Use the empty XAMPP `root` password only for isolated local development. Create a dedicated password-protected database account before a real deployment.

## Django

```dotenv
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=replace-with-a-long-random-value
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000
DJANGO_TIME_ZONE=UTC
DJANGO_SECURE_SSL_REDIRECT=false
```

Ghana and UTC currently share the same UTC offset. Keeping MariaDB and Django on UTC also avoids requiring XAMPP named time-zone tables.

## Redis and Jobs

```dotenv
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=30
JOB_TIMEOUT_SECONDS=300
```

## Upload and Privacy Controls

```dotenv
CAPTURED_FACES_DIR=private_uploads
MAX_UPLOAD_BYTES=5242880
MAX_IMAGE_PIXELS=16000000
ENABLE_DEV_IMAGE_ENDPOINT=false
ENABLE_FACE_IDENTIFICATION=false
DELETE_RAW_IMAGE_AFTER_PROCESSING=true
```

## Inference Controls

```dotenv
EMBEDDING_MODEL=ArcFace
MATCH_THRESHOLD=0.45
EMOTION_DETECTOR_BACKEND=retinaface
EMOTION_EXPAND_PERCENTAGE=10
EMOTION_SMOOTHING_FRAMES=3
EMOTION_SMOOTHING_WINDOW_SECONDS=4
EMOTION_MIN_SAMPLES=2
EMOTION_MIN_CONFIDENCE=0.55
EMOTION_MIN_MARGIN=0.10
EMOTION_MIN_FACE_SIZE=80
EMOTION_MIN_SHARPNESS=25
EMOTION_MIN_BRIGHTNESS=25
EMOTION_MAX_BRIGHTNESS=230
```

## Desktop Agent

```dotenv
INGESTION_API_URL=http://localhost:8001/v1/snapshots
DEVICE_API_KEY=
CAPTURE_INTERVAL_SECONDS=10
CAMERA_BUSY_RETRY_SECONDS=15
CAMERA_WARMUP_FRAMES=3
CAMERA_ACTIVE_SECONDS=2
MAX_IMAGES_PER_CAMERA_SESSION=3
BURST_IMAGE_INTERVAL_SECONDS=0.75
SHIFT_END_HOUR=17
RESUME_WARNING_SECONDS=300
```

Do not put secrets directly in `docker-compose.yml`, source code, notebooks, screenshots, issue reports, or Git history.

---

# Local Development

## Requirements

```text
Windows 10 or later
Python 3.10
Git
XAMPP with MySQL/MariaDB
Docker Desktop for Redis
Webcam for capture testing
Internet access for the initial model download
```

## 1. Clone the Repository

```powershell
git clone https://github.com/GT-Raph/Smart-Customer-Sentiment-Analysis.git
cd Smart-Customer-Sentiment-Analysis
git switch non-saas
```

## 2. Create the Main Environment

Run from the repository root:

```powershell
py -3.10 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Create the Environment File

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env`, replace `DJANGO_SECRET_KEY`, and review every setting before continuing.

## 4. Create the XAMPP Database

Start MySQL in the XAMPP Control Panel. In phpMyAdmin, run:

```sql
CREATE DATABASE smart_sentiment
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

The application defaults to:

```text
Database: smart_sentiment
User:     root
Password: empty
Host:     127.0.0.1
Port:     3306
```

## 5. Apply Migrations

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py migrate
```

## 6. Create an Administrator

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py createsuperuser
```

## 7. Create a Branch

Start Django temporarily if it is not running:

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py runserver 8000
```

Open `http://127.0.0.1:8000/admin/`, sign in, and create an active `Branch`.

The branch ID is the number in its Django admin change-page URL.

## 8. Create a Device Key

Replace `2` with the real branch ID:

```powershell
$branchId = 2
.\.venv\Scripts\python.exe emotion_dashboard\manage.py create_device_key --branch $branchId --name front-desk-camera --pc-name ACCRA01-CAMERA
```

Copy the generated key into `DEVICE_API_KEY` in `.env`. It is displayed only once.

## 9. Start Redis

Start Docker Desktop and wait until the Linux engine reports that it is running:

```powershell
if (-not (Test-Path .compose.env)) { New-Item -ItemType File .compose.env | Out-Null }
docker compose --env-file .compose.env up -d redis
```

The empty `.compose.env` file prevents Docker Compose from reading application passwords from `.env` and interpreting dollar signs as variable references. The running services still load application configuration from `.env`.

## 10. Create the Worker Environment

The TensorFlow environment is intentionally separate from the dashboard/API environment:

```powershell
py -3.10 -m venv .venv-worker
.\.venv-worker\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r api_server\requirements-worker.txt
```

The first worker start downloads the RetinaFace weights, approximately 119 MB, into the current user's DeepFace cache.

---

# Running the System

Keep XAMPP MySQL, Redis, Django, FastAPI, the worker, and the camera agent running.

## Terminal 1: Django

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py runserver 8000
```

Open `http://127.0.0.1:8000/`.

## Terminal 2: FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

Health check:

```text
http://127.0.0.1:8001/health
```

## Terminal 3: Worker

```powershell
.\.venv-worker\Scripts\python.exe -m api_server.worker_main
```

## Terminal 4: Camera Agent

Start it in the foreground first:

```powershell
.\.venv\Scripts\python.exe clients\device_agent.py
```

After verification, stop it with `Ctrl+C` and launch it without a console window:

```powershell
Start-Process -FilePath ".\.venv\Scripts\pythonw.exe" -ArgumentList "clients\device_agent.py" -WorkingDirectory (Get-Location)
```

Do not run foreground and background copies at the same time.

## Pause and Resume Controls

Use the notification-area menu, or run:

```powershell
.\.venv\Scripts\python.exe clients\device_agent.py --pause 30 --reason "Customer video call"
.\.venv\Scripts\python.exe clients\device_agent.py --status
.\.venv\Scripts\python.exe clients\device_agent.py --resume
```

Console-only troubleshooting:

```powershell
.\.venv\Scripts\python.exe clients\device_agent.py --no-tray
```

## Stop the System

Use `Ctrl+C` in foreground Python terminals. Exit the camera agent through its notification-area menu.

Stop Redis without deleting its volume:

```powershell
docker compose --env-file .compose.env stop redis
```

---

# Legacy Jupyter Notebooks

The notebooks under `research/legacy_notebooks/` are retained for supervised research and migration work. They are not the production capture/worker path.

Install the optional environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebook.txt
.\.venv\Scripts\python.exe -m jupyter lab research\legacy_notebooks\desktop_capture.ipynb
```

Current notebook roles:

```text
desktop_capture.ipynb   Supervised API capture experiment
main.ipynb              Sample-image expression analysis; no database
process-faces.ipynb     Legacy XAMPP batch-processing experiment
prototype.ipynb         Legacy live-preview prototype
```

`process-faces.ipynb` and `prototype.ipynb` still refer to parts of the older research schema. Their XAMPP connection is configured, but their legacy processing cells are not drop-in replacements for the current worker.

Stop the tray agent before opening a notebook that accesses the camera.

---

# Docker Compose

Redis can be started independently:

```powershell
docker compose --env-file .compose.env up -d redis
```

The dashboard, API, and worker also have Dockerfiles:

```powershell
docker compose --env-file .compose.env up --build
```

In full Compose mode:

- XAMPP MariaDB remains on the Windows host.
- Application containers connect through `host.docker.internal`.
- Redis runs in the Compose network.
- API and worker share the `private_uploads` volume.
- Worker model files use the persistent `model_cache` volume.
- The desktop camera agent still runs on the camera PC, outside Docker.

XAMPP must permit the configured database account to connect from Docker. Do not expose port 3306 publicly.

---

# Database Architecture

## Development Database

The non-SaaS branch uses XAMPP MySQL/MariaDB for Django, FastAPI, and the worker.

```text
Django --------+
               |
FastAPI -------+----> smart_sentiment
               |
RQ worker -----+
```

SQLite is supported only for isolated Django tests by setting:

```dotenv
DATABASE_ENGINE=sqlite
```

The FastAPI and worker data layers require MySQL/MariaDB.

## Connection Lifetime

`DB_CONN_MAX_AGE=0` prevents Django from reusing a connection that belonged to a stopped XAMPP process. MySQL must still be running before database-backed pages can work.

## MariaDB 10.4 Compatibility

Some XAMPP releases bundle MariaDB 10.4, below Django 5.2's supported MariaDB 10.5 minimum. The project includes a local compatibility backend enabled by:

```dotenv
XAMPP_ALLOW_MARIADB_10_4=true
```

This exists for local compatibility. Upgrade MariaDB for a maintained production deployment.

---

# Migrations

Django migrations are authoritative for the relational schema.

Apply migrations:

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py migrate
```

Check for model changes without migrations:

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py makemigrations --check --dry-run
```

Migration `0002_remove_saas_tenancy` removes SaaS organization, plan, subscription, billing, and quota data while retaining branches, users, devices, visitors, and snapshots.

Read [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) before moving data from the SaaS edition or another database engine.

---

# Security and Privacy Requirements

## Authorization

- Enforce branch scope in Django querysets.
- Treat superuser checks as privileged operations.
- Do not rely only on hidden navigation links.
- Keep image endpoints authenticated.
- Test direct URL access with users from another branch.

## Device Security

- Issue a separate key to every device.
- Never reuse administrator credentials as device credentials.
- Revoke a lost or retired device in Django admin.
- Never log or commit full device keys.
- Keep the ingestion service behind TLS outside localhost.

## Image and Biometric Privacy

- Keep `DELETE_RAW_IMAGE_AFTER_PROCESSING=true` unless retention has been explicitly approved.
- Keep `ENABLE_FACE_IDENTIFICATION=false` unless persistent matching is necessary and approved.
- Keep private upload directories outside public static/media serving paths.
- Restrict filesystem and backup access.
- Define retention for snapshots, vectors, embeddings, logs, exports, and backups.
- Provide notice and document consent or another lawful basis before live collection.
- Complete legal and privacy review for the deployment jurisdiction.

## Expression-Model Safety

- Describe results as facial-expression classifications, not verified emotions.
- Preserve `uncertain` instead of forcing low-confidence labels.
- Do not use results for decisions about an individual.
- Monitor performance across lighting, camera position, face size, and demographic groups.
- Validate changes against a consented, representative evaluation set.

## File Upload Security

The ingestion service validates both declared and decoded file formats, size, dimensions, and pixel count. Production deployments should additionally consider reverse-proxy request limits, malware controls where required, and centralized security logging.

## Secrets

Never hard-code or commit:

```text
DJANGO_SECRET_KEY
Database passwords
Device API keys
Production Redis credentials
Private image paths
Face embeddings
Exported reports
```

---

# Production Security Configuration

Minimum production settings:

```dotenv
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=sentiment.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://sentiment.example.com
DJANGO_SECURE_SSL_REDIRECT=true
ENABLE_DEV_IMAGE_ENDPOINT=false
ENABLE_FACE_IDENTIFICATION=false
DELETE_RAW_IMAGE_AFTER_PROCESSING=true
```

Also:

```text
Use HTTPS through a managed reverse proxy
Restrict MariaDB and Redis to trusted hosts
Use a dedicated least-privilege database account
Protect backups with encryption and access controls
Configure centralized logs and error monitoring
Set operating-system service recovery policies
Test device-key revocation
Test database and image-store restoration
Review retention and deletion behavior
```

---

# Testing

## API, Worker, and Camera Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Django Tests

```powershell
$env:DATABASE_ENGINE = "sqlite"
.\.venv\Scripts\python.exe emotion_dashboard\manage.py test monitor -v 2
Remove-Item Env:DATABASE_ENGINE
```

## Schema and System Checks

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py check
.\.venv\Scripts\python.exe emotion_dashboard\manage.py makemigrations --check --dry-run
```

## Deployment Check

Use production-like environment values before running:

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py check --deploy
```

## Continuous Integration

GitHub Actions currently performs:

```text
Python 3.10 dependency installation
Python bytecode compilation
API and worker unit tests
Django migration checks
Django monitor tests with SQLite
Django deployment checks
```

---

# Recommended Test Expansion

Future test work should include:

```text
Real camera-resolution quality calibration
Expression confusion matrices
Multi-frame consensus with concurrent workers
Redis interruption and recovery
XAMPP restart recovery
Local upload-queue overflow behavior
Device revocation during capture
Cross-branch direct URL attempts
Raw-image deletion failures
Backup and restore drills
Long-running worker memory tests
RetinaFace throughput benchmarks
Accessibility and reduced-motion checks
```

---

# Known Implementation Gaps

## 1. Facial Expression Is Not Internal Emotion

The model cannot determine a person's internal state. Even a visible smile may be misclassified because of lighting, pose, occlusion, camera quality, model limitations, or an ambiguous probability distribution.

## 2. Production Calibration Is Still Required

The included confidence, margin, brightness, sharpness, and smoothing defaults are starting points. They have not been certified against a representative production dataset from every intended branch.

## 3. Private Storage Is Single-Host

The included private directory/shared volume suits a one-host installation. Multi-host deployment requires private object storage, strict authorization, and short-lived signed access.

## 4. Automated Notification Delivery Is Not Implemented

Notification preferences exist in the dashboard, but scheduled weekly email delivery and negative-expression alert delivery require a reviewed background service.

## 5. No Packaged Windows Service

The camera agent supports a tray process and console mode, but the repository does not yet include a signed installer, Windows Service package, automatic updater, or enterprise deployment policy.

## 6. MariaDB 10.4 Is Compatibility-Only

The XAMPP compatibility backend permits local use of MariaDB 10.4, but that database line is end-of-life and should not be treated as the preferred production target.

## 7. Legacy Notebooks Use an Older Research Schema

Some notebook processing cells require schema migration before they can replace current application services.

---

# Performance Considerations

- RetinaFace is more accurate than Haar-based detection but is more computationally expensive.
- The worker environment keeps models loaded to avoid per-job startup cost.
- Three-frame bursts increase inference work; monitor RQ queue depth and processing latency.
- Keep capture interval and API rate limit consistent.
- Store only necessary raw images and embeddings.
- Add workers only after testing database concurrency and session-consensus behavior.
- Use indexes already defined for branch/time, status/time, visitor/time, and session ID queries.

---

# Deployment Architecture

A production-oriented single-host layout is:

```text
Camera PCs
    |
    | HTTPS + device keys
    v
Reverse proxy / TLS
    |
    +---- Django dashboard
    |
    +---- FastAPI ingestion
              |
              +---- Redis/RQ ---- Worker
              |
              +---- Private upload storage
              |
              +---- MariaDB
```

The dashboard should not be exposed through Django's development server in production. Use Gunicorn or another supported application server behind a reverse proxy.

---

# Production Deployment Checklist

- [ ] Confirm the `non-saas` branch is deployed.
- [ ] Set `DJANGO_DEBUG=false`.
- [ ] Generate a strong Django secret.
- [ ] Configure allowed hosts and trusted origins.
- [ ] Enable HTTPS and secure redirect.
- [ ] Create a least-privilege MariaDB account.
- [ ] Upgrade from end-of-life MariaDB versions.
- [ ] Restrict MariaDB and Redis network access.
- [ ] Issue one device key per camera.
- [ ] Confirm revoked devices are rejected.
- [ ] Keep raw-image deletion enabled unless approved otherwise.
- [ ] Complete privacy, notice, consent, and retention review.
- [ ] Calibrate quality and confidence thresholds.
- [ ] Benchmark RetinaFace and queue throughput.
- [ ] Configure service supervision and automatic recovery.
- [ ] Configure centralized logs and alerts.
- [ ] Back up MariaDB and test restoration.
- [ ] Protect or replace single-host private storage.
- [ ] Run all automated tests and deployment checks.

---

# Backup and Restore

Back up at minimum:

```text
MariaDB smart_sentiment database
Deployment configuration outside Git
Device inventory and revocation records
Approved retained private images, if retention is enabled
Operational documentation
```

Do not store plaintext secrets in ordinary database dumps or documentation.

A backup is not considered reliable until restoration has been tested on an isolated environment.

---

# Logging and Monitoring

Production monitoring should cover:

```text
Django HTTP errors
FastAPI validation and authentication failures
Redis availability
RQ queue depth and failed jobs
Worker processing latency
Model initialization failures
MariaDB availability and storage growth
Device last-seen timestamps
Camera busy/retry frequency
Local queued-capture growth
Raw-image deletion failures
Disk utilization
```

Never write full device keys, database passwords, raw face images, or embeddings to application logs.

---

# Git Ignore

The repository excludes local and sensitive artifacts including:

```text
.env and .env.* except .env.example
.venv and .venv-worker
Python caches
Test caches and coverage output
SQLite databases
Private uploads
Queued captures
Captured faces
Media and collected static files
IDE settings
Notebook checkpoints
Build and package artifacts
```

Review `git status` before every commit. A virtual environment appearing in Source Control means the ignore rules or repository location should be corrected before committing.

---

# Coding Standards

## Django

- Keep branch authorization in server-side query helpers.
- Use the custom user model through Django settings.
- Represent schema changes with migrations.
- Keep forms responsible for validating user-editable settings.
- Use POST for state-changing actions such as logout.

## API

- Authenticate before accepting image data.
- Validate declared and decoded file content.
- Keep TensorFlow outside the FastAPI process.
- Do not expose another device's job status.
- Preserve bounded size, pixel, and rate limits.

## Worker

- Normalize model vectors before classification.
- Preserve `uncertain` for weak evidence.
- Keep quality thresholds configurable.
- Delete private files on success, rejection, and terminal failure when configured.
- Add tests for model-library API changes.

## Camera Agent

- Do not add a live preview to the bank deployment path.
- Release the camera before processing and upload.
- Keep manual pauses finite and automatically expiring.
- Bound the local retry queue.
- Never include the device secret in logs.

## Secrets

Read secrets from environment variables. Never hard-code:

```text
Passwords
DJANGO_SECRET_KEY
Device API keys
Database URLs or credentials
Production service tokens
```

---

# Git Workflow

Check the current edition and worktree:

```powershell
git branch --show-current
git status
```

This repository currently keeps the self-hosted edition on:

```text
non-saas
```

Create a focused branch from the edition you intend to change:

```powershell
git switch non-saas
git switch -c feature/short-description
```

Examples:

```text
feature/camera-health-dashboard
feature/private-object-storage
feature/expression-calibration

fix/device-retry-backoff
fix/session-consensus
fix/branch-access-scope

hardening/device-authentication
hardening/private-image-retention
hardening/upload-validation
```

Before committing:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe emotion_dashboard\manage.py check
.\.venv\Scripts\python.exe emotion_dashboard\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe emotion_dashboard\manage.py test monitor -v 2
git status
```

Commit and push:

```powershell
git add .
git commit -m "Describe the focused change"
git push -u origin feature/short-description
```

Do not merge `main` and `non-saas` wholesale. Review and port specific commits when a change belongs in both editions.

---

# Pull Request Requirements

A pull request should identify:

1. What changed
2. Why it changed
3. Whether it targets `main` or `non-saas`
4. Branch-access impact
5. Device and camera impact
6. Database and migration impact
7. API compatibility impact
8. Worker/model impact
9. Privacy and retention impact
10. Environment-variable impact
11. Performance impact
12. Tests performed
13. Deployment and rollback steps

Model changes should additionally identify:

```text
Evaluation dataset used?
Per-expression precision/recall measured?
Confidence calibration changed?
Quality thresholds changed?
Demographic performance reviewed?
Queue throughput measured?
Historical results affected?
```

---

# Current Implementation Scope

## Implemented

```text
[x] Django authentication
[x] Installation administrator access
[x] Branch-scoped normal-user access
[x] Branch management
[x] User dashboard preferences
[x] Password change and reset routes

[x] Registered camera devices
[x] One-time device-key creation
[x] Hashed device-key storage
[x] Device revocation
[x] Device last-seen tracking

[x] Silent desktop capture
[x] Bounded multi-frame camera bursts
[x] Camera release between capture windows
[x] Camera-busy retry
[x] Finite persisted pause controls
[x] Local failed-upload queue

[x] FastAPI image ingestion
[x] MIME and decoded-format validation
[x] Upload byte and pixel limits
[x] Per-device Redis rate limiting
[x] Device-scoped status endpoint

[x] Redis/RQ background processing
[x] Warm DeepFace model process
[x] RetinaFace detection and alignment
[x] Image-quality rejection
[x] Multi-frame probability consensus
[x] Uncertain-result thresholding
[x] Optional ArcFace matching
[x] Raw-image deletion by default

[x] Dashboard overview
[x] Branch comparison
[x] Branch detail analytics
[x] Expression analytics
[x] Reports and CSV output
[x] Responsive Sentiment Grid UI

[x] XAMPP MySQL/MariaDB support
[x] MariaDB 10.4 local compatibility backend
[x] Dockerfiles and Docker Compose
[x] GitHub Actions CI
[x] Automated API, worker, camera, migration, and UI tests
```

---

# Not Production-Complete

```text
Representative real-world model calibration
Independent fairness and accuracy evaluation
Production legal/privacy approval
Packaged and signed Windows camera installer
Enterprise camera deployment and updates
Multi-host private object storage
Centralized structured logging
Error monitoring and alerting
Automated database backup and restore validation
Automated notification delivery
Comprehensive load and long-duration testing
Documented disaster recovery targets
```

---

# Development Priorities

## P0 - Safety, Privacy, and Accuracy

```text
Build a consented representative validation dataset
Measure per-expression precision and recall
Calibrate uncertainty and quality thresholds
Review performance across demographic groups
Complete legal/privacy and retention review
Prevent use in individual financial decisions
```

## P1 - Operational Reliability

```text
Package the camera agent as a managed Windows application
Add health telemetry without collecting raw imagery
Monitor RQ queue depth and worker latency
Test Redis, MariaDB, and network recovery
Add controlled device update and rollback
```

## P2 - Storage and Deployment

```text
Add private object storage for multi-host deployment
Add signed short-lived image access if retention is approved
Upgrade MariaDB beyond compatibility-only versions
Document backup and disaster-recovery targets
```

## P3 - Test Expansion

```text
Camera hardware integration tests
Long-running worker tests
Concurrent consensus tests
Cross-branch authorization tests
Accessibility tests
Production load tests
```

---

# Definition of Done

A change is complete only when the applicable items are satisfied.

- [ ] Requirement is implemented.
- [ ] The correct product edition and branch were used.
- [ ] Branch authorization remains enforced.
- [ ] Device authentication remains enforced.
- [ ] Privacy and retention impact was reviewed.
- [ ] Raw-image deletion behavior was verified.
- [ ] Database changes have reviewed migrations.
- [ ] New environment variables are documented.
- [ ] API compatibility was reviewed.
- [ ] Worker throughput impact was reviewed.
- [ ] Camera release and pause behavior remain correct.
- [ ] Confidence and uncertainty behavior were tested.
- [ ] Django system checks pass.
- [ ] Migration dry-run passes.
- [ ] Automated tests pass.
- [ ] Manual workflow was tested where hardware is involved.
- [ ] Production and rollback impact is documented.
- [ ] README and supporting documentation are updated.

---

# Collaborator Checklist

## Before Development

- [ ] Read this README.
- [ ] Confirm whether the work targets `main` or `non-saas`.
- [ ] Activate the correct Python environment.
- [ ] Run `git status`.
- [ ] Run Django system checks.
- [ ] Review relevant models and migrations.
- [ ] Review branch authorization.
- [ ] Review privacy and retention impact.
- [ ] Reproduce the reported issue.
- [ ] Create a focused branch when appropriate.

## Before Review

- [ ] Run API, worker, and camera tests.
- [ ] Run Django tests.
- [ ] Run the migration dry-run.
- [ ] Test administrator access.
- [ ] Test normal branch-user access.
- [ ] Test direct URLs from the wrong branch.
- [ ] Test invalid and revoked device keys.
- [ ] Review uploaded-file cleanup.
- [ ] Review database changes.
- [ ] Review new secrets and configuration.
- [ ] Review camera and worker performance.
- [ ] Document deployment and rollback.
- [ ] Update this README.

---

# Reporting Technical Issues

Include:

```text
Title:

Environment:
Local / Test / Production

Edition and branch:
main / non-saas / feature branch

Component:
Django / FastAPI / Worker / Redis / XAMPP / Camera Agent / Notebook

User type:
Administrator / Branch user / Device

Branch ID or name:

Steps to reproduce:
1.
2.
3.

Expected:

Actual:

URL or command:

HTTP status:

Traceback:

Job ID:

Device PC name:

Snapshot status:

Data impact:
[ ] User
[ ] Branch
[ ] Device
[ ] Snapshot
[ ] Private image
[ ] Expression result
[ ] Cross-branch exposure
[ ] None known
```

Do not include:

```text
Passwords
DJANGO_SECRET_KEY
DEVICE_API_KEY
Database passwords
Redis credentials
Session cookies
CSRF tokens
Raw face images without approved handling
Face embeddings
Unredacted customer information
```

---

# Project Status

```text
Django dashboard             Implemented
Branch access control        Implemented
Device authentication        Implemented
FastAPI ingestion            Implemented
Redis/RQ processing          Implemented
Silent camera capture        Implemented
Finite pause controls        Implemented
RetinaFace alignment         Implemented
Expression classification    Implemented; calibration required
Multi-frame consensus        Implemented
Uncertainty handling         Implemented
Raw-image deletion           Implemented
XAMPP integration            Implemented
Reports and analytics        Implemented
Automated tests              Implemented; expansion recommended
Windows service packaging    Not implemented
Multi-host private storage   Not implemented
Production observability     Not implemented
Independent model audit      Not completed
```

> These indicators describe implementation present in the repository. They are not a certification of model accuracy, legal compliance, security, or production readiness.

---

# Documentation Rule

Update this README whenever the project changes:

```text
Branch access behavior
Device authentication
Capture timing
Pause controls
Upload validation
API routes
Worker models
Expression thresholds
Quality thresholds
Image retention
Face-identification behavior
Database models
Migrations
Environment variables
Deployment commands
Known limitations
```

When documentation conflicts with source code, treat the current implementation in these files as authoritative:

```text
api_server/config.py
api_server/face_api.py
api_server/worker.py
api_server/db_utils.py
clients/device_agent.py
emotion_dashboard/emotion_dashboard/settings.py
emotion_dashboard/monitor/models.py
emotion_dashboard/monitor/access.py
emotion_dashboard/monitor/views.py
emotion_dashboard/monitor/urls.py
emotion_dashboard/monitor/migrations/
tests/
```

---

# License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

---

<p align="center">
  <strong>Sentiment Grid</strong>
</p>

<p align="center">
  Silent Capture · Authenticated Ingestion · Background Inference · Branch Analytics
</p>

<p align="center">
  <sub>Django · FastAPI · XAMPP MariaDB · Redis/RQ · DeepFace · RetinaFace</sub>
</p>
