# Smart Customer Sentiment Analysis

> A multi-bank facial recognition and emotion-analysis platform for capturing customer sentiment at branch workstations and presenting tenant-isolated analytics through a centralized dashboard.

![Django](https://img.shields.io/badge/Django-5.2.11-092E20?style=flat-square\&logo=django\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.2-009688?style=flat-square\&logo=fastapi\&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10.x-3776AB?style=flat-square\&logo=python\&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Primary%20Database-4169E1?style=flat-square\&logo=postgresql\&logoColor=white)
![DeepFace](https://img.shields.io/badge/DeepFace-0.0.98-FF6F00?style=flat-square)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.13.0-FF6F00?style=flat-square\&logo=tensorflow\&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.11-5C3EE8?style=flat-square\&logo=opencv\&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

---

## Overview

**Smart Customer Sentiment Analysis** is a distributed facial-analysis system designed for banks and other branch-based environments.

The current implementation consists of three primary runtime components:

1. An **OpenCV desktop capture client** installed on customer-facing workstations.
2. A **FastAPI facial-analysis service** responsible for authentication, branch resolution, facial embeddings, visitor matching, emotion inference, image storage, and database persistence.
3. A **Django analytics dashboard** used for tenant-scoped sentiment monitoring, branch analytics, reporting, configuration, and administration.

The platform supports multiple banks and multiple branches while preventing facial records, embeddings, snapshots, and analytics from being mixed across bank tenants.

The primary processing pipeline is:

```text
Customer
   │
   ▼
Workstation Camera
   │
   ▼
desktop_capture.py
   │
   │ HTTPS / HTTP
   │ X-Bank-Code
   │ X-API-Key
   │ pc_name
   ▼
FastAPI Analysis Service
   │
   ├── Authenticate Bank
   ├── Resolve Branch
   ├── Extract Face
   ├── Generate ArcFace Embedding
   ├── Match Visitor
   ├── Detect Emotion
   └── Persist Snapshot
   │
   ▼
PostgreSQL
   │
   ▼
Django Analytics Dashboard
```

The current implementation includes:

* Webcam-based customer face capture
* Customer-region filtering
* Face stability checks
* Blur and brightness validation
* Eye detection
* Candidate-frame scoring
* Automatic capture
* Multi-bank API authentication
* Automatic branch resolution from Windows PC names
* DeepFace facial extraction
* ArcFace facial embeddings
* Cosine-distance visitor matching
* ULID-based visitor identification
* Facial emotion inference
* Full emotion-vector persistence
* PostgreSQL storage
* Tenant-isolated Django analytics
* Branch-level reporting
* Protected captured-image access
* Offline workstation capture queue
* Automatic queued-capture retry
* Bank API-key rotation
* Bank and branch configuration
* Dashboard preferences
* CSV report export

> **Development status**
>
> The repository contains an implemented end-to-end capture, processing, persistence, and analytics pipeline.
>
> Production deployment still requires infrastructure-specific validation, biometric-data governance, monitoring, backup procedures, performance testing, and deployment hardening.

---

# Architecture

## High-Level Design

```text
┌─────────────────────────────┐
│      Customer Presence      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Workstation Camera     │
│           OpenCV            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    Desktop Capture Client   │
│                             │
│ ROI filtering               │
│ Face detection              │
│ Stability validation        │
│ Quality scoring             │
│ Candidate selection         │
│ Offline queue               │
└──────────────┬──────────────┘
               │
               │ multipart/form-data
               │ X-Bank-Code
               │ X-API-Key
               │ pc_name
               ▼
┌─────────────────────────────┐
│       FastAPI Service       │
│                             │
│ Bank authentication         │
│ Branch resolution           │
│ DeepFace extraction         │
│ ArcFace embeddings          │
│ Cosine matching             │
│ Emotion analysis            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         PostgreSQL          │
│                             │
│ Banks                       │
│ Branches                    │
│ Visitors                    │
│ Sentiment snapshots         │
│ Users                       │
│ Preferences                 │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Django Dashboard       │
│                             │
│ Tenant isolation            │
│ Branch analytics            │
│ Emotion analytics           │
│ Reports                     │
│ Settings                    │
└─────────────────────────────┘
```

---

# Runtime Components

## Desktop Capture Client

The workstation capture application is implemented in:

```text
desktop_capture.py
```

Its responsibility is to acquire suitable facial images before sending them to the central analysis API.

The client does not perform final visitor identification or emotion classification locally.

### Capture Pipeline

```text
Camera Frame
    ↓
Customer ROI
    ↓
Haar Face Detection
    ↓
Face Position Stability
    ↓
Quality Inspection
    ↓
Candidate Sampling
    ↓
Best Candidate Selection
    ↓
JPEG Encoding
    ↓
API Submission
```

### Quality Controls

The current capture client evaluates:

* Minimum face width
* Minimum face height
* Face-to-frame area ratio
* Blur / sharpness
* Mean brightness
* Percentage of very dark pixels
* Percentage of very bright pixels
* Eye detection
* Face stability across frames
* Intersection-over-Union stability
* Candidate quality score
* Face absence
* Capture cooldown

The client uses OpenCV Haar cascades for preliminary workstation-side face and eye detection.

### Default Camera Configuration

```text
CAMERA_INDEX=0
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=30
```

### Customer Region of Interest

The default capture region is expressed as percentages of the camera frame:

```text
ROI_LEFT=0.18
ROI_TOP=0.06
ROI_RIGHT=0.82
ROI_BOTTOM=0.96
```

This allows the workstation to restrict automatic capture to the expected customer position.

### Default Quality Parameters

```text
MIN_FACE_WIDTH_PIXELS=120
MIN_FACE_HEIGHT_PIXELS=120
MIN_FACE_AREA_RATIO=0.035

BLUR_THRESHOLD=45.0

MIN_BRIGHTNESS=45.0
MAX_BRIGHTNESS=215.0

MAX_DARK_PIXEL_PERCENT=0.58
MAX_BRIGHT_PIXEL_PERCENT=0.38
```

### Stability Configuration

```text
STABLE_FRAMES_REQUIRED=6
STABILITY_IOU_THRESHOLD=0.55

SAMPLE_WINDOW_SECONDS=1.2
MIN_GOOD_CANDIDATES=4

DETECTION_INTERVAL_FRAMES=2
FACE_ABSENCE_RESET_SECONDS=1.8
CAPTURE_COOLDOWN_SECONDS=5.0
```

These parameters may be changed through environment variables without modifying the capture source.

---

# Offline Capture Queue

The desktop client contains a local retry mechanism for temporary API or network failures.

Default configuration:

```text
OFFLINE_QUEUE_DIR=offline_queue
QUEUE_RETRY_INTERVAL_SECONDS=30.0
MAX_OFFLINE_QUEUE_FILES=300
```

Processing behavior:

```text
Capture
   │
   ▼
Submit to API
   │
   ├── 2xx ───────────────► Success
   │
   ├── 4xx ───────────────► Reject
   │
   └── Network / 5xx
              │
              ▼
        Offline Queue
              │
              ▼
        Periodic Retry
```

When a retryable failure occurs, the workstation stores:

```text
<capture>.jpg
<capture>.json
```

The metadata file records information such as:

* Bank code
* PC name
* Creation timestamp
* Last API error
* Blur measurement
* Brightness measurement
* Quality score

Successful retries remove the queued image and associated metadata.

Client errors in the `4xx` range are treated as rejected requests rather than temporary network failures.

---

# FastAPI Analysis Service

The facial-analysis API is implemented under:

```text
api_server/
```

Primary modules:

```text
api_server/
│
├── config.py
├── db_utils.py
├── face_api.py
├── face_utils.py
├── requirements.txt
│
└── api/
    └── index.py
```

The API identifies itself as:

```text
Multi-bank Customer Sentiment API
```

Current API version:

```text
3.0
```

---

# API Endpoints

## Service Status

```http
GET /
```

Returns basic service information.

---

## Health Check

```http
GET /health
```

The health endpoint performs a PostgreSQL connectivity test using:

```sql
SELECT 1;
```

A database failure returns:

```text
503 Service Unavailable
```

---

## Face Upload

```http
POST /upload-face
```

Successful processing returns:

```text
201 Created
```

### Required Headers

```http
X-Bank-Code: <bank-code>
X-API-Key: <api-key>
```

### Request Format

```text
Content-Type: multipart/form-data
```

Fields:

```text
file      Image upload
pc_name   Workstation computer name
```

Supported content types:

```text
image/jpeg
image/png
image/webp
```

Default maximum upload size:

```text
5 MiB
```

---

# API Authentication

Every image-processing request must authenticate against a bank.

Authentication uses:

```text
X-Bank-Code
X-API-Key
```

The API does not store raw bank API keys.

When a key is configured, the application stores:

```text
SHA-256(raw_api_key)
```

Verification uses:

```python
hmac.compare_digest(...)
```

Authentication flow:

```text
Bank Code
    +
Raw API Key
    ↓
Normalize Bank Code
    ↓
Load Active Bank
    ↓
SHA-256 Supplied Key
    ↓
Constant-Time Hash Comparison
    ↓
Authenticated Bank
```

An invalid or missing API credential results in:

```text
401 Unauthorized
```

Database failures during authentication result in:

```text
503 Service Unavailable
```

---

# Automatic Branch Resolution

The workstation is not allowed to select a branch directly.

The desktop client submits:

```text
pc_name
```

The API resolves the branch using the authenticated bank and configured branch PC prefixes.

Example:

```text
Bank: FIDELITY_GH

Branch:
    name: Ridge Towers
    code: RIDGE_TOWERS
    pc_prefix: FBLRGE

Workstation:
    FBLRGE001
```

Matching logic:

```text
FBLRGE001
   ↓
startswith("FBLRGE")
   ↓
Ridge Towers
```

Prefix matching is:

* Bank-scoped
* Case-normalized
* Restricted to active branches
* Based on the start of the workstation name

If multiple configured prefixes match, the **longest prefix wins**.

Example:

```text
FBL
FBLRGE
```

For:

```text
FBLRGE001
```

the API selects:

```text
FBLRGE
```

rather than the shorter `FBL` prefix.

A workstation that does not match any active branch returns:

```text
403 Forbidden
```

---

# Face Processing Pipeline

After bank authentication and branch resolution, processing follows:

```text
Uploaded Image
      ↓
Validate Content Type
      ↓
Validate Upload Size
      ↓
OpenCV Decode
      ↓
Save Original Capture
      ↓
DeepFace.extract_faces()
      ↓
Crop Individual Face
      ↓
CLAHE Enhancement
      ↓
DeepFace.represent()
      ↓
ArcFace Embedding
      ↓
Tenant-Scoped Visitor Matching
      ↓
DeepFace Emotion Analysis
      ↓
Database Transaction
      ↓
Visitor + Snapshot
```

Image processing is currently protected by a process-level:

```python
threading.Lock()
```

This serializes the main DeepFace processing section within each running API process.

---

# Facial Embeddings

The default embedding model is:

```text
ArcFace
```

Configured using:

```env
EMBEDDING_MODEL=ArcFace
```

DeepFace generates a facial embedding using:

```python
DeepFace.represent(
    img_path=enhanced_face,
    model_name=EMBEDDING_MODEL,
    enforce_detection=False,
)
```

The resulting embedding is stored as JSON-compatible numerical data in PostgreSQL.

---

# Face Enhancement

Before representation and emotion analysis, the extracted face is converted to grayscale and enhanced using CLAHE:

```text
BGR Face
   ↓
Grayscale
   ↓
CLAHE
   ↓
BGR
   ↓
DeepFace
```

Current CLAHE configuration:

```text
clipLimit=2.0
tileGridSize=(8, 8)
```

---

# Visitor Identification

Previously stored embeddings are loaded only from the authenticated bank.

The API does not compare a customer's face against visitor embeddings belonging to another bank.

Conceptually:

```text
Authenticated Bank
       ↓
Load Latest Stored Embedding
per Visitor in that Bank
       ↓
Generate Current Embedding
       ↓
Cosine Distance
       ↓
Threshold Comparison
       ↓
Known / New Visitor
```

The matching function calculates:

```text
cosine_similarity =
    dot(known, current)
    /
    (norm(known) × norm(current))
```

and:

```text
cosine_distance =
    1 - cosine_similarity
```

The current default threshold is:

```env
MATCH_THRESHOLD=0.45
```

A visitor is considered a match when:

```text
distance < threshold
```

If no stored visitor satisfies the threshold, a new face identifier is generated.

---

# Visitor Identifiers

New visitors receive a ULID:

```python
str(ulid.new())
```

Example form:

```text
01JXXXXXXXXXXXXXXX
```

ULIDs are also used for processing job identifiers.

Visitor identity is unique within a bank.

The same `face_id` value can technically exist in separate bank tenants because the database uniqueness constraint is:

```text
(bank, face_id)
```

rather than globally on `face_id`.

---

# Emotion Analysis

Emotion inference uses:

```python
DeepFace.analyze(
    img_path=face_image,
    actions=["emotion"],
    enforce_detection=False,
)
```

The typical DeepFace emotion space includes:

```text
angry
disgust
fear
happy
sad
surprise
neutral
```

For each valid face, the API extracts:

```text
dominant_emotion
confidence
full_emotion_vector
```

Example logical result:

```json
{
  "face_id": "01J...",
  "emotion": "happy",
  "confidence": 91.42
}
```

The complete emotion vector is persisted separately from the dominant emotion.

---

# Multi-Face Processing

The API uses:

```python
DeepFace.extract_faces(...)
```

and iterates through all detected faces.

When multiple valid faces occur in one uploaded image, each face can generate its own snapshot.

The first snapshot uses the primary job ID.

Additional faces receive indexed job IDs:

```text
<job_id>
<job_id>-1
<job_id>-2
...
```

The desktop capture client defaults to:

```env
UPLOAD_FACE_CROP=True
```

which normally reduces workstation submissions to the selected customer face crop.

---

# Image Storage

Accepted uploads are persisted under:

```text
captured_faces/
```

The current storage hierarchy is:

```text
captured_faces/
└── <BANK_CODE>/
    └── <BRANCH_CODE>/
        └── <PC_NAME>/
            └── <JOB_ID>.jpg
```

Example:

```text
captured_faces/
└── FIDELITY_GH/
    └── RIDGE_TOWERS/
        └── FBLRGE001/
            └── 01J....jpg
```

The database stores the relative path rather than exposing a direct public file URL.

Before writing an image, the API validates that the generated path remains inside:

```text
CAPTURED_FACES_ROOT
```

If facial processing fails, the newly stored image is removed.

---

# Database Architecture

PostgreSQL is the primary database.

Direct FastAPI database operations use:

```text
psycopg2
```

The Django dashboard uses:

```text
Django ORM
```

Both components operate on the same logical schema.

The current core application tables are:

```text
tenant_bank
tenant_branch
analytics_visitor
analytics_snapshot
tenant_bank_settings
monitor_user_preference
```

Django also creates its normal authentication, permission, session, and migration tables.

---

# Core Data Model

## Bank

Table:

```text
tenant_bank
```

Important fields include:

```text
id
name
code
api_key_hash
api_key_rotated_at
is_active
created_at
```

Bank codes are normalized to uppercase.

---

## Branch

Table:

```text
tenant_branch
```

Important fields:

```text
id
bank_id
name
code
pc_prefix
location
is_active
```

Constraints include:

```text
UNIQUE(bank, code)
UNIQUE(bank, pc_prefix)
```

Branch codes and PC prefixes are normalized to uppercase.

---

## Visitor

Table:

```text
analytics_visitor
```

Important fields:

```text
id
bank_id
face_id
first_seen
last_seen
```

Constraint:

```text
UNIQUE(bank, face_id)
```

A visitor therefore belongs explicitly to one bank tenant.

---

## Captured Snapshot

Table:

```text
analytics_snapshot
```

Important fields:

```text
id
job_id
bank_id
branch_id
visitor_id
pc_name
image_path
timestamp
emotion
confidence
emotion_vector
embedding
processed
status
processing_error
```

Supported statuses:

```text
pending
done
failed
```

Current successful API writes use:

```text
processed = TRUE
status = done
```

Indexes are defined for:

```text
(bank, timestamp)
(branch, timestamp)
(bank, visitor, timestamp)
```

---

## Bank Settings

Table:

```text
tenant_bank_settings
```

Current configuration fields include:

```text
timezone
image_retention_days
record_retention_days
delete_images_after_retention
offline_after_minutes
```

Defaults include:

```text
timezone = Africa/Accra
image_retention_days = 30
record_retention_days = 365
delete_images_after_retention = True
offline_after_minutes = 15
```

These settings are represented in the current data model and administration interface.

Any automated retention/deletion process should be verified separately before assuming configured retention values are being executed as scheduled background jobs.

---

# Database Write Transaction

Visitor and sentiment records are persisted inside the same PostgreSQL transaction.

Conceptually:

```text
Begin Transaction
      ↓
INSERT visitor
or update last_seen
      ↓
INSERT snapshot
      ↓
Commit
```

On processing failure:

```text
Rollback
```

Visitor creation uses PostgreSQL conflict handling:

```text
ON CONFLICT (bank_id, face_id)
DO UPDATE SET
    last_seen = EXCLUDED.last_seen
```

This keeps a returning visitor's `last_seen` timestamp current without generating a duplicate visitor row.

---

# Django Dashboard

The Django application is located under:

```text
emotion_dashboard/
```

Main application:

```text
monitor
```

Current routed interfaces include:

```text
/
logout/
dashboard/
branches/
branch/<branch_id>/
emotion-analytics/
reports/
settings/
snapshot/<snapshot_id>/image/
```

The dashboard provides:

* Authentication
* Tenant-scoped dashboard metrics
* Branch overview
* Branch-specific analytics
* Emotion analytics
* Reporting
* CSV export
* Dashboard settings
* User settings
* Bank settings
* Branch configuration
* API-key rotation
* Protected snapshot-image retrieval

---

# Dashboard Authorization Model

The current authorization hierarchy is:

```text
Superuser
    ↓
All Banks
    ↓
All Branches


Bank Administrator
    ↓
Assigned Bank
    ↓
All Branches in Bank


Branch User
    ↓
Assigned Bank
    ↓
Assigned Branch Only
```

A non-superuser must belong to a bank.

If a user is assigned directly to a branch, the model automatically derives the associated bank.

A branch cannot be assigned to a user if that branch belongs to a different bank.

---

# Tenant Isolation

Tenant isolation is enforced in the dashboard using centralized queryset helpers.

Core helpers include:

```text
visible_branches(user)
visible_snapshots(user)
visible_visitors(user)
get_visible_branch_or_404(...)
require_bank_admin(...)
```

The general access pattern is:

```text
Authenticated User
      ↓
Determine User Bank
      ↓
Determine Optional Branch
      ↓
Construct Scoped QuerySet
      ↓
Load Requested Object
      ↓
Return or 404 / Deny
```

### Mandatory Tenant Rules

Contributors should preserve the following invariants:

1. Never query bank-owned analytics without tenant scoping.
2. A bank user must not access another bank's branches.
3. A bank user must not access another bank's visitors.
4. A bank user must not access another bank's snapshots.
5. A branch user must remain restricted to the assigned branch.
6. Face matching must remain bank-scoped.
7. API authentication must resolve the bank before branch resolution.
8. The workstation must not submit a branch ID directly.
9. Branch resolution must remain bank-specific.
10. Captured-image access must use the same tenant scope as snapshot access.

---

# Protected Image Access

Captured face images are intentionally stored outside Django's normal public static/media paths.

Images are retrieved through:

```text
snapshot/<snapshot_id>/image/
```

The view:

1. Requires authentication.
2. Filters the snapshot through the user's tenant permissions.
3. Resolves the configured captured-face root.
4. Resolves the stored relative image path.
5. Rejects paths outside the configured root.
6. Returns the file only if it exists.

This prevents direct public enumeration of stored captured faces.

---

# API-Key Rotation

Bank API keys can be rotated from the dashboard settings workflow.

New keys are generated using:

```python
secrets.token_urlsafe(32)
```

The bank model requires a raw key length of at least:

```text
24 characters
```

Only the SHA-256 digest is persisted.

The previous key becomes invalid after rotation.

All capture clients belonging to that bank must therefore be updated with the newly issued credential.

---

# Technology Stack

| Layer                 | Technology                         |
| --------------------- | ---------------------------------- |
| Desktop Capture       | Python, OpenCV                     |
| API                   | FastAPI                            |
| Dashboard             | Django 5.2.11                      |
| Language              | Python                             |
| Face Analysis         | DeepFace 0.0.98                    |
| Embedding Model       | ArcFace                            |
| ML Runtime            | TensorFlow 2.13.0                  |
| Primary Database      | PostgreSQL                         |
| API DB Driver         | psycopg2                           |
| Dashboard DB Layer    | Django ORM                         |
| Numerical Processing  | NumPy                              |
| HTTP Client           | Requests                           |
| Identifier Generation | ULID                               |
| Local Dashboard DB    | SQLite — optional development mode |

---

# Repository Structure

The current repository is organized approximately as follows:

```text
Smart-Customer-Sentiment-Analysis/
│
├── api_server/
│   ├── api/
│   │   └── index.py
│   ├── config.py
│   ├── db_utils.py
│   ├── face_api.py
│   ├── face_utils.py
│   ├── requirements.txt
│   └── vercel.json
│
├── emotion_dashboard/
│   ├── emotion_dashboard/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── monitor/
│   │   ├── migrations/
│   │   ├── templates/
│   │   ├── admin.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── settings_views.py
│   │   ├── tenant.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   └── manage.py
│
├── emotion_detection_system/
│   └── prototype / notebook material
│
├── docs/
│   ├── api.md
│   ├── architecture.md
│   ├── contributing.md
│   └── usage.md
│
├── desktop_capture.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

The root `desktop_capture.py`, `api_server/`, Django `emotion_dashboard/`, current models, migrations, and tests should be treated as the primary implementation when documentation conflicts with older prototype material.

---

# Local Development

## Requirements

Recommended environment:

* Python 3.10.x
* Git
* PostgreSQL
* Camera access for workstation testing
* Sufficient disk space for TensorFlow/DeepFace models and captured images

CPU inference is supported.

A compatible GPU environment may improve inference performance, but GPU configuration depends on the TensorFlow and CUDA versions used by the deployment host.

---

# 1. Clone Repository

```powershell
git clone <repository-url>
cd Smart-Customer-Sentiment-Analysis
```

---

# 2. Create Virtual Environment

Windows:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

---

# 3. Install Dependencies

Install the complete repository dependency set:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The API also contains a smaller service-specific dependency file:

```powershell
pip install -r api_server/requirements.txt
```

Use the root requirements file when developing the complete system.

---

# 4. Environment Configuration

Create:

```text
.env
```

in the project root.

A representative development configuration is:

```env
# --------------------------------------------------
# PostgreSQL
# --------------------------------------------------

DB_NAME=customer_sentiment
DB_USER=postgres
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=5432
DB_SSLMODE=disable


# --------------------------------------------------
# Django
# --------------------------------------------------

DJANGO_DEBUG=True
DJANGO_SECRET_KEY=replace-with-development-secret
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

TIME_ZONE=Africa/Accra


# --------------------------------------------------
# Face API
# --------------------------------------------------

EMBEDDING_MODEL=ArcFace
MATCH_THRESHOLD=0.45
MAX_UPLOAD_BYTES=5242880

CAPTURED_FACES_ROOT=./captured_faces


# --------------------------------------------------
# Desktop Capture Client
# --------------------------------------------------

FACE_API_URL=http://127.0.0.1:8001/upload-face

BANK_CODE=<configured-bank-code>
BANK_API_KEY=<configured-bank-api-key>

CAMERA_INDEX=0
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=30

PREVIEW_ENABLED=True
UPLOAD_FACE_CROP=True
```

For PostgreSQL environments requiring SSL:

```env
DB_SSLMODE=require
```

---

# Environment Variables

## Database

```text
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
DB_SSLMODE
DB_CONNECT_TIMEOUT_SECONDS
```

---

## API

```text
CAPTURED_FACES_ROOT
EMBEDDING_MODEL
MATCH_THRESHOLD
MAX_UPLOAD_BYTES
```

---

## Django

```text
DJANGO_DEBUG
DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS
TIME_ZONE

SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS
```

---

## Desktop Capture

```text
FACE_API_URL

BANK_CODE
BANK_API_KEY

CAMERA_INDEX
CAMERA_WIDTH
CAMERA_HEIGHT
CAMERA_FPS

REQUEST_TIMEOUT_SECONDS

PREVIEW_ENABLED
UPLOAD_FACE_CROP
JPEG_QUALITY

ROI_LEFT
ROI_TOP
ROI_RIGHT
ROI_BOTTOM

MIN_FACE_WIDTH_PIXELS
MIN_FACE_HEIGHT_PIXELS
MIN_FACE_AREA_RATIO

BLUR_THRESHOLD

MIN_BRIGHTNESS
MAX_BRIGHTNESS

MAX_DARK_PIXEL_PERCENT
MAX_BRIGHT_PIXEL_PERCENT

STABLE_FRAMES_REQUIRED
STABILITY_IOU_THRESHOLD

SAMPLE_WINDOW_SECONDS
MIN_GOOD_CANDIDATES

DETECTION_INTERVAL_FRAMES

FACE_ABSENCE_RESET_SECONDS
CAPTURE_COOLDOWN_SECONDS

OFFLINE_QUEUE_DIR
QUEUE_RETRY_INTERVAL_SECONDS
MAX_OFFLINE_QUEUE_FILES
```

---

# 5. Database Setup

The database schema should be managed using Django migrations.

Move into:

```powershell
cd emotion_dashboard
```

Run:

```powershell
py manage.py migrate
```

Do not manually recreate the older MySQL schema contained in previous versions of the project documentation.

The current implementation uses PostgreSQL-backed Django models.

---

# 6. Optional SQLite Development Mode

The Django dashboard supports SQLite for local development.

Set:

```env
DB_ENGINE=sqlite
```

Then:

```powershell
py manage.py migrate
```

This option applies to the Django application.

The FastAPI processing service directly uses PostgreSQL through `psycopg2`, so full end-to-end API testing requires PostgreSQL.

---

# 7. Create Dashboard Administrator

From:

```text
emotion_dashboard/
```

run:

```powershell
py manage.py createsuperuser
```

---

# 8. Configure Bank and Branch

Before the desktop client can upload captures, the database must contain:

```text
Bank
   ↓
API Key
   ↓
Active Branch
   ↓
PC Prefix
```

Example:

```text
Bank:
    Name: Fidelity Bank Ghana
    Code: FIDELITY_GH

Branch:
    Name: Ridge Towers
    Code: RIDGE_TOWERS
    PC Prefix: FBLRGE
```

A computer named:

```text
FBLRGE001
```

will then resolve automatically to that branch.

---

# 9. Start FastAPI

From the repository root:

```powershell
uvicorn api_server.face_api:app --host 0.0.0.0 --port 8001
```

Development reload:

```powershell
uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001 --reload
```

Useful endpoints:

| Purpose | URL                            |
| ------- | ------------------------------ |
| Service | `http://127.0.0.1:8001/`       |
| Health  | `http://127.0.0.1:8001/health` |
| OpenAPI | `http://127.0.0.1:8001/docs`   |

---

# 10. Start Django Dashboard

Open another terminal:

```powershell
cd emotion_dashboard
py manage.py runserver 8000
```

Useful URLs:

| Purpose           | URL                                        |
| ----------------- | ------------------------------------------ |
| Login             | `http://127.0.0.1:8000/`                   |
| Dashboard         | `http://127.0.0.1:8000/dashboard/`         |
| Branches          | `http://127.0.0.1:8000/branches/`          |
| Emotion Analytics | `http://127.0.0.1:8000/emotion-analytics/` |
| Reports           | `http://127.0.0.1:8000/reports/`           |
| Settings          | `http://127.0.0.1:8000/settings/`          |
| Django Admin      | `http://127.0.0.1:8000/admin/`             |

---

# 11. Start Desktop Capture

Ensure `.env` contains:

```env
FACE_API_URL=http://127.0.0.1:8001/upload-face
BANK_CODE=<bank-code>
BANK_API_KEY=<bank-api-key>
```

Then run:

```powershell
python desktop_capture.py
```

The capture machine must have:

* Camera access
* Network access to the FastAPI service
* Valid bank credentials
* A Windows/computer name matching an active branch prefix

The workstation name is determined automatically using:

```python
socket.gethostname()
```

---

# API Response Example

A successful request returns a structure similar to:

```json
{
  "status": "processed",
  "job_id": "01J...",
  "bank": {
    "code": "FIDELITY_GH",
    "name": "Fidelity Bank Ghana"
  },
  "branch": {
    "code": "RIDGE_TOWERS",
    "name": "Ridge Towers",
    "matched_pc_prefix": "FBLRGE"
  },
  "pc_name": "FBLRGE001",
  "faces": [
    {
      "face_id": "01J...",
      "emotion": "happy",
      "confidence": 91.42
    }
  ]
}
```

---

# HTTP Error Behavior

Important response classes include:

| Status | Meaning                                         |
| ------ | ----------------------------------------------- |
| `400`  | Invalid PC name or invalid image                |
| `401`  | Missing or invalid bank credentials             |
| `403`  | Workstation is not assigned to an active branch |
| `413`  | Uploaded image exceeds configured size          |
| `415`  | Unsupported image content type                  |
| `422`  | No valid face detected / processed              |
| `500`  | Face or emotion processing failed               |
| `503`  | Database unavailable                            |

The desktop client handles:

```text
2xx → success
4xx → reject
5xx/network → queue and retry
```

---

# Testing

The Django application currently contains tenant-isolation tests.

Existing tests cover scenarios including:

```text
✓ Bank A dashboard excludes Bank B data
✓ Bank B dashboard excludes Bank A data
✓ Bank A cannot open Bank B branch
✓ Bank A cannot open Bank B captured image
✓ Branch user cannot open another bank branch
✓ Same face ID can exist in separate banks
✓ Bank administrator cannot inject another bank's branch filter
```

Run tests from:

```text
emotion_dashboard/
```

using:

```powershell
py manage.py test monitor
```

For SQLite-backed local test execution:

```powershell
$env:DB_ENGINE="sqlite"
$env:DJANGO_DEBUG="True"

py manage.py test monitor
```

---

# Quality Gates

Before significant changes:

```powershell
cd emotion_dashboard

py manage.py check
py manage.py makemigrations --check --dry-run
py manage.py test
```

For production settings review:

```powershell
py manage.py check --deploy
```

The capture client and API should additionally be tested against:

```text
Valid bank + valid branch PC
Invalid API key
Unknown bank
Unknown workstation
Malformed image
Oversized image
Unsupported file type
No face
Returning visitor
New visitor
Multiple faces
Database unavailable
API unavailable
Offline queue recovery
```

---

# Testing Expectations

Tenant-sensitive features should always include at least two banks.

Example:

```text
BANK_A
  └── BRANCH_A

BANK_B
  └── BRANCH_B
```

Then verify:

```text
BANK_A user
    ↓
Attempt BANK_B resource
    ↓
Access MUST be denied
```

Face-identification testing should verify that:

```text
BANK_A embedding set
        ≠
BANK_B embedding set
```

A customer captured under one bank must not be matched against stored visitors from another bank.

---

# Security Requirements

## API Credentials

Never commit:

```text
BANK_API_KEY
DB_PASSWORD
DJANGO_SECRET_KEY
.env
production credentials
```

---

## Tenant Isolation

Never:

* Remove bank filtering from embedding lookup
* Match visitors globally across banks
* Accept arbitrary branch IDs from capture clients
* Trust URL IDs without tenant filtering
* Serve captured images directly from public static paths
* Expose another bank's reports or analytics
* Disable dashboard authentication for convenience

---

## Captured Images

Captured facial images are application data.

They should not be committed to Git.

The existing `.gitignore` excludes repository-level:

```text
captured_faces/
```

Face images should remain outside publicly served static paths.

---

## Path Safety

Any filesystem access based on stored or calculated paths must ensure that the resolved path remains beneath the configured root.

The current image-upload and image-serving code both perform root-containment checks.

This behavior must be preserved.

---

## Transport Security

Production workstation-to-API traffic should use:

```text
HTTPS
```

rather than unencrypted HTTP.

Bank API keys are application credentials and must not be transmitted over untrusted plaintext networks.

---

## Django Security

The current production-mode Django settings enable controls including:

```text
SESSION_COOKIE_HTTPONLY
CSRF_COOKIE_HTTPONLY
SECURE_CONTENT_TYPE_NOSNIFF
X_FRAME_OPTIONS = DENY
```

When:

```text
DJANGO_DEBUG=False
```

the configuration also enables secure-cookie behavior and supports:

```text
SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS
```

---

# Biometric Data Considerations

This system processes facial images and facial embeddings.

Operational deployments should therefore treat the following as sensitive application data:

```text
Captured facial images
Facial embeddings
Visitor identifiers
Visit timestamps
Branch history
Emotion-analysis results
```

Retention, access, deletion, backup, monitoring, and operational procedures should be explicitly defined for the deployment environment.

The application currently contains configurable image and record-retention values, but deployment teams should verify the mechanism responsible for enforcing those policies before relying on them operationally.

---

# Database Migrations

Create migrations only when Django models change:

```powershell
cd emotion_dashboard

py manage.py makemigrations
py manage.py migrate
```

Migration rules:

* Review generated migrations.
* Do not modify already-deployed migration history casually.
* Use a new migration to correct deployed schema changes.
* Test migrations before production deployment.
* Back up production data before destructive schema operations.
* Keep FastAPI direct SQL compatible with the Django-managed schema.

The last point is particularly important because the FastAPI service directly references tables such as:

```text
tenant_bank
tenant_branch
analytics_visitor
analytics_snapshot
```

Renaming these models, tables, or fields requires coordinated API changes.

---

# Cross-Component Contract

Changes to the system must account for dependencies between the three main components.

Example:

```text
Django Model Change
        ↓
Database Schema Change
        ↓
FastAPI SQL May Break
        ↓
Capture API May Fail
        ↓
Desktop Queue Accumulates
```

Before changing database structure, verify:

```text
emotion_dashboard/monitor/models.py
api_server/db_utils.py
api_server/face_api.py
dashboard views
dashboard tests
```

---

# Performance Considerations

Facial inference is significantly more expensive than normal API request processing.

Current processing characteristics include:

* DeepFace model initialization
* Face extraction
* ArcFace embedding generation
* Emotion inference
* Loading known visitor embeddings
* NumPy cosine-distance comparison
* Synchronous PostgreSQL writes
* Local filesystem image writes
* Process-level facial-processing lock

Current visitor matching loads the latest usable stored embedding for each visitor belonging to the current bank.

As visitor counts grow, performance should be measured before assuming the current in-memory comparison strategy will scale indefinitely.

Potential future optimization areas include:

```text
Embedding indexing
Vector database / pgvector
Worker queue
Model worker processes
Batch processing
Caching
Dedicated inference service
Object storage
Horizontal API scaling
```

These are architectural options, not requirements of the current implementation.

---

# Deployment Architecture

A production deployment should keep workstation capture, machine-learning inference, database storage, and dashboard presentation logically separated.

Recommended topology:

```text
BRANCH WORKSTATIONS
desktop_capture.py
        │
        │ HTTPS
        ▼
┌────────────────────────┐
│ Reverse Proxy / TLS    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ FastAPI Inference API  │
│ DeepFace / TensorFlow  │
└───────┬─────────┬──────┘
        │         │
        │         ▼
        │   Persistent
        │   Image Storage
        │
        ▼
┌────────────────────────┐
│ PostgreSQL             │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Django Dashboard       │
└───────────┬────────────┘
            │
            ▼
      Authenticated
      Staff Browser
```

The inference API requires sufficient CPU/RAM and persistent model availability.

Local face-image storage also requires a persistent filesystem unless the storage layer is replaced.

---

# Serverless Deployment Note

The repository contains:

```text
api_server/vercel.json
api_server/api/index.py
```

for a Vercel-style API entry point.

However, production deployment of the current DeepFace/TensorFlow workload should be validated against:

* Runtime size limits
* Model download/loading behavior
* Memory limits
* Execution timeout
* Cold starts
* Persistent filesystem requirements
* PostgreSQL connectivity
* Concurrent inference behavior

A traditional VM, container service, or dedicated inference host may be more appropriate for persistent machine-learning workloads depending on infrastructure requirements.

---

# Backup & Restore

At minimum, production backup procedures should cover two separate data classes:

```text
PostgreSQL
    +
Captured Face Images
```

Backing up PostgreSQL alone does not back up:

```text
captured_faces/
```

A complete restore therefore requires:

```text
Database Backup
       +
Image Storage Backup
       ↓
Restore
       ↓
Verify Relative Image Paths
       ↓
Start FastAPI
       ↓
Start Django
       ↓
Verify Snapshot Access
       ↓
Verify Visitor Matching
```

Restore testing should be performed against a disposable environment rather than directly against production.

---

# Logging & Monitoring

The production environment should monitor at least:

```text
FastAPI availability
Database availability
API 5xx rate
API 401/403 rate
Processing latency
DeepFace inference failures
Unknown workstation errors
Offline queue growth
Disk utilization
Captured-face storage growth
Database storage
Django errors
Authentication failures
```

The `/health` endpoint can be used as the initial FastAPI database-aware health probe.

---

# Git Ignore

Runtime and credential files should remain outside version control.

Current important exclusions include:

```gitignore
/captured_faces/

received_images.log
api_responses.log

.venv/
.env
```

Recommended additional local exclusions include:

```gitignore
/offline_queue/

__pycache__/
*.pyc

emotion_dashboard/db.sqlite3

*.log
```

Review existing tracked files before changing ignore rules because adding a path to `.gitignore` does not automatically remove files that are already tracked.

---

# Coding Standards

## Python

* Follow PEP 8.
* Keep tenant scoping explicit.
* Keep ML processing isolated from dashboard presentation logic.
* Keep database writes transactional.
* Normalize external identifiers before comparisons.
* Validate all client-controlled input.
* Do not duplicate credential-validation logic unnecessarily.
* Preserve filesystem path-containment checks.
* Use environment variables for deployment configuration.
* Do not hard-code production credentials.

---

# FastAPI

Request flow should remain approximately:

```text
Receive Request
      ↓
Authenticate Bank
      ↓
Validate PC Name
      ↓
Validate Upload
      ↓
Resolve Branch
      ↓
Persist Image
      ↓
Process Face
      ↓
Persist Transaction
      ↓
Return Structured Result
```

The client must not select its own branch.

---

# Django Views

Tenant-sensitive dashboard views should follow:

```text
Authenticate User
      ↓
Determine User Scope
      ↓
Build Tenant QuerySet
      ↓
Apply Allowed Filters
      ↓
Load Object
      ↓
Render / Export / Stream
```

Do not use unrestricted:

```python
CapturedSnapshot.objects.get(...)
```

for user-facing tenant-sensitive routes.

Use the centralized tenant-scoping helpers.

---

# Database Code

FastAPI direct SQL must:

* Include bank scope
* Use parameterized queries
* Maintain model/table compatibility
* Use transactions for related writes
* Avoid interpolating user input into SQL strings

Example:

```python
cursor.execute(
    """
    SELECT ...
    FROM analytics_snapshot
    WHERE bank_id = %s
    """,
    (bank_id,),
)
```

---

# Machine-Learning Code

Changes to:

```text
EMBEDDING_MODEL
MATCH_THRESHOLD
face enhancement
DeepFace extraction
emotion analysis
```

can materially change identity matching behavior.

Such changes should be evaluated against a controlled validation dataset before production rollout.

A threshold change is not merely a cosmetic configuration change.

It changes the false-match / false-non-match tradeoff.

---

# Git Workflow

Verify the active branch before development:

```powershell
git branch --show-current
git status
```

Update the repository's primary branch according to the repository's current branch policy.

Create a feature branch:

```powershell
git checkout -b feature/short-description
```

Examples:

```text
feature/vector-search
feature/capture-health-monitor
feature/image-retention-worker

fix/cross-bank-image-access
fix/offline-queue-retry
fix/branch-prefix-matching

hardening/api-rate-limits
hardening/production-settings

ml/embedding-threshold-validation
ml/model-evaluation
```

Before committing:

```powershell
cd emotion_dashboard

py manage.py check
py manage.py test

git status
```

Commit:

```powershell
git add .
git commit -m "Add concise description of change"
```

Push:

```powershell
git push -u origin feature/short-description
```

---

# Pull Requests

A pull request should identify:

1. What changed
2. Why it changed
3. Runtime component affected
4. Database impact
5. Migration impact
6. Tenant-security impact
7. Facial-identification impact
8. Environment-variable changes
9. Tests added or modified
10. Manual validation performed
11. Deployment impact

ML-related pull requests should additionally state:

```text
Embedding model:
Previous threshold:
New threshold:
Validation dataset:
Match-rate impact:
Known regressions:
```

---

# Current Implementation Scope

## Implemented

* Webcam capture
* Customer ROI
* Haar face detection
* Eye detection
* Capture quality scoring
* Automatic capture
* Capture cooldown
* Offline queue
* Queue retry
* FastAPI processing
* Bank API authentication
* API-key hashing
* API-key rotation
* Multi-bank tenancy
* Multi-branch tenancy
* Automatic PC-to-branch resolution
* DeepFace face extraction
* ArcFace embeddings
* Cosine-distance matching
* ULID visitor IDs
* Emotion detection
* Emotion confidence storage
* Emotion-vector storage
* Embedding persistence
* Captured-image persistence
* PostgreSQL backend
* Django dashboard
* Tenant-restricted dashboard queries
* Branch analytics
* Emotion analytics
* Reports
* CSV export
* Protected image serving
* Bank settings
* Branch settings
* Dashboard preferences
* Tenant-isolation tests

---

# Not Evidenced as Complete Runtime Features

The current repository should not be assumed to provide complete implementations of the following unless additional infrastructure exists outside this repository:

```text
Automated biometric-retention scheduler
Distributed ML task queue
Vector-indexed face search
Liveness / anti-spoofing detection
Centralized object-storage integration
Automatic backup orchestration
Full infrastructure monitoring
API rate limiting
Production alert delivery
Horizontal inference orchestration
```

These may be future extensions or external deployment responsibilities.

---

# Development Priorities

Technical hardening priorities for the current architecture should focus on the existing pipeline before expanding the feature surface.

## P0 — Security & Data Isolation

```text
Expand cross-bank API tests
Expand branch-user authorization tests
Verify captured-image isolation
Add API abuse/rate controls
Review biometric-data retention enforcement
Validate production secret handling
```

## P1 — Reliability

```text
Add API integration tests
Add desktop-client tests where practical
Test offline queue recovery
Add structured logging
Add central error monitoring
Validate database failure handling
Validate persistent image storage
```

## P2 — ML Validation

```text
Benchmark ArcFace threshold
Measure false-match rate
Measure false-non-match rate
Validate emotion inference conditions
Evaluate difficult lighting
Evaluate camera positions
Evaluate multiple faces
Evaluate demographic performance
```

## P3 — Performance

```text
Measure visitor-embedding lookup cost
Profile DeepFace inference
Evaluate model preload strategy
Evaluate pgvector or vector indexing
Evaluate worker architecture
Evaluate concurrent API throughput
```

---

# Definition of Done

A system change is complete only when applicable checks are satisfied.

* [ ] Requirement is implemented
* [ ] Bank isolation is preserved
* [ ] Branch isolation is preserved
* [ ] API authentication is preserved
* [ ] PC-to-branch resolution is validated
* [ ] Database writes remain transactional
* [ ] FastAPI SQL matches Django schema
* [ ] Captured-image access remains protected
* [ ] Path traversal protections remain intact
* [ ] Offline behavior is considered
* [ ] ML behavior is tested where affected
* [ ] Environment changes are documented
* [ ] Migrations are reviewed
* [ ] Django checks pass
* [ ] Automated tests pass
* [ ] Manual end-to-end capture is tested where applicable
* [ ] Documentation is updated
* [ ] Production implications are documented

---

# Collaborator Checklist

## Before Development

* [ ] Read this README
* [ ] Review `desktop_capture.py`
* [ ] Review `api_server/config.py`
* [ ] Review `api_server/face_api.py`
* [ ] Review `api_server/db_utils.py`
* [ ] Review `api_server/face_utils.py`
* [ ] Review `emotion_dashboard/monitor/models.py`
* [ ] Review `emotion_dashboard/monitor/tenant.py`
* [ ] Review relevant dashboard views
* [ ] Review current migrations
* [ ] Run existing tests
* [ ] Confirm current environment variables
* [ ] Reproduce the issue
* [ ] Create a dedicated Git branch

## Before Review

* [ ] Run Django checks
* [ ] Run tests
* [ ] Test with two banks where tenant-sensitive
* [ ] Test branch-user restrictions
* [ ] Test invalid bank API key
* [ ] Test unknown workstation
* [ ] Test direct URL manipulation
* [ ] Review database migrations
* [ ] Review API/database schema compatibility
* [ ] Document new environment variables
* [ ] Test capture workflow if affected
* [ ] Test API failure behavior if affected
* [ ] Test offline queue if affected

---

# Repository Safety

Do not commit:

```text
.env
API keys
Database passwords
Django secret keys
Production credentials
Captured customer faces
Unnecessary biometric exports
Authentication tokens
```

Review logs before committing them because operational logs may contain:

```text
PC names
face IDs
timestamps
image paths
processing information
```

---

# Reporting Issues

When reporting a technical issue, include:

```text
Title:

Environment:
Local / Staging / Production

Component:
Desktop Capture / FastAPI / Django / PostgreSQL

Bank:
Branch:
PC name:

Steps to reproduce:
1.
2.
3.

Expected:
Actual:

HTTP status:
API response:

Relevant logs:

Data impact:
[ ] Cross-bank exposure
[ ] Captured image
[ ] Facial embedding
[ ] Emotion record
[ ] Visitor identity
[ ] Database
[ ] None known
```

Do not include:

```text
Raw API keys
Passwords
Database credentials
Django secret keys
Production access tokens
Unredacted customer facial images in public issues
```

---

# Project Status

```text
Desktop Camera Capture       ██████████  Implemented
Capture Quality Gate         ██████████  Implemented
Offline Queue                ██████████  Implemented
FastAPI Processing           ██████████  Implemented
Bank Authentication          ██████████  Implemented
Branch Auto-Detection        ██████████  Implemented
ArcFace Embeddings           ██████████  Implemented
Visitor Matching             ██████████  Implemented
Emotion Analysis             ██████████  Implemented
PostgreSQL Persistence       ██████████  Implemented
Multi-Bank Isolation         ██████████  Implemented
Django Dashboard             ██████████  Implemented
Branch Analytics             ██████████  Implemented
CSV Reporting                ██████████  Implemented
Tenant Tests                 ███████░░░  Present / expandable
Retention Automation         ███░░░░░░░  Requires verification
ML Performance Scaling       ███░░░░░░░  Future hardening
Production Observability     ███░░░░░░░  Deployment dependent
```

> These indicators describe implementation presence in the repository and do not constitute production-readiness certification.

---

# Documentation

The repository currently includes:

```text
docs/
├── api.md
├── architecture.md
├── contributing.md
└── usage.md
```

Some older documentation may describe the previous folder-monitoring and MySQL implementation.

Documentation should be synchronized with the current:

```text
desktop_capture.py
FastAPI API
PostgreSQL schema
multi-bank architecture
automatic branch resolution
Django dashboard
```

before relying on it for deployment.

---

# License

This project is licensed under the **MIT License**.

See:

```text
LICENSE
```

for the complete license terms.

---

<p align="center">
  <strong>Smart Customer Sentiment Analysis</strong>
</p>

<p align="center">
  Multi-bank architecture · Facial embeddings · Emotion analysis · Branch analytics · Tenant isolation
</p>

<p align="center">
  <sub>OpenCV workstation capture · FastAPI inference · PostgreSQL persistence · Django analytics</sub>
</p>
