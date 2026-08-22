# Smart Customer Sentiment Analysis System

A multi-tenant facial emotion analysis and customer sentiment monitoring platform designed for banks and branch-based organisations.

The system automatically captures customer faces from configured workstation cameras, analyses facial emotion using DeepFace, identifies returning visitors using facial embeddings, and stores sentiment data for reporting and analytics.

Each workstation communicates with a central FastAPI service. The API authenticates the bank, automatically identifies the branch from the workstation's computer name, performs face recognition and emotion analysis, and stores the resulting records in PostgreSQL.

A Django-based dashboard provides authorised users with bank-level and branch-level sentiment analytics, visitor statistics, reports, system settings, and operational monitoring.

## Core Features

* Automatic customer face capture using a workstation webcam
* Face quality and stability checks before capture
* Customer-only configurable camera region of interest
* Facial emotion detection using DeepFace
* ArcFace facial embeddings for visitor recognition
* Detection of new and returning visitors
* Unique ULID-based face identification
* Multi-bank and multi-branch architecture
* Automatic branch identification using workstation PC-name prefixes
* Bank API-key authentication
* PostgreSQL data persistence
* Django analytics and reporting dashboard
* Bank and branch access control
* Emotion confidence and full emotion-vector storage
* Offline capture queue with automatic retry
* Configurable image and data-retention settings
* Dashboard preferences and automatic refresh options

## System Architecture

```text
Customer
   │
   ▼
Workstation Camera
   │
   ▼
desktop_capture.py
   │
   │  HTTPS / HTTP
   │  X-Bank-Code
   │  X-API-Key
   │  PC Name
   ▼
FastAPI Face Analysis Service
   │
   ├── Bank Authentication
   ├── Automatic Branch Detection
   ├── Face Detection
   ├── ArcFace Embedding Generation
   ├── Visitor Matching
   └── Emotion Analysis
   │
   ▼
PostgreSQL Database
   │
   ├── Banks
   ├── Branches
   ├── Visitors
   └── Sentiment Snapshots
   │
   ▼
Django Dashboard
   ├── Dashboard
   ├── Branch Analytics
   ├── Emotion Analytics
   ├── Reports
   └── Settings
```

## Main Components

### Desktop Capture Client

`desktop_capture.py` runs on the customer-facing workstation.

It uses OpenCV to monitor the configured camera, detect faces within a customer region of interest, perform quality checks, and automatically select a suitable image for analysis.

Quality checks include:

* face size
* face stability
* image sharpness
* brightness
* eye detection
* face area
* duplicate-capture prevention

Captured images are submitted to the central API together with the workstation's computer name.

If the API cannot be reached, captures can be stored in the local offline queue and retried later.

### FastAPI Analysis Service

The FastAPI service is located in:

```text
api_server/
```

Its primary face-processing endpoint is:

```text
POST /upload-face
```

The API:

1. Authenticates the bank.
2. Reads the workstation PC name.
3. Determines the appropriate branch using its configured PC-name prefix.
4. Detects faces in the uploaded image.
5. Generates an ArcFace embedding.
6. Compares the embedding with known visitors belonging to the same bank.
7. Assigns an existing face ID or generates a new ULID.
8. Performs facial emotion analysis.
9. Stores the snapshot and visitor information in PostgreSQL.

### Django Analytics Dashboard

The dashboard is located in:

```text
emotion_dashboard/
```

It provides authenticated access to:

* overall sentiment dashboard
* branch overview
* individual branch analytics
* emotion analytics
* reports
* account and system settings
* bank and branch administration

Access to data is restricted according to the user's assigned bank and branch.

## Technology Stack

* Python
* OpenCV
* DeepFace
* ArcFace
* TensorFlow
* FastAPI
* Django
* PostgreSQL
* psycopg2
* NumPy
* Requests
* ULID

## API Endpoints

The current API exposes:

```text
GET  /
GET  /health
POST /upload-face
```

### Upload Authentication

`POST /upload-face` requires the following headers:

```text
X-Bank-Code: <bank-code>
X-API-Key: <bank-api-key>
```

The multipart request contains:

```text
file      Image file
pc_name   Workstation computer name
```

Accepted image formats include JPEG, PNG, and WebP.

## Database

PostgreSQL is the primary database used by the application.

The core application models include:

```text
tenant_bank
tenant_branch
analytics_visitor
analytics_snapshot
tenant_bank_settings
monitor_user_preference
```

Django migrations should be used to create and update the database schema rather than manually creating the old MySQL tables shown in previous versions of this README.

For local dashboard development, SQLite can optionally be enabled using:

```text
DB_ENGINE=sqlite
```
