# Smart Customer Sentiment Analysis

A multi-bank SaaS application for customer facial-expression analytics. Teller
camera clients upload cropped face images to an authenticated FastAPI service,
the service records tenant-scoped results in Supabase PostgreSQL, and authorized
bank users view analytics in the Django dashboard.

> The output is a facial-expression signal, not proof of a person's true
> emotion. Deploy only with an appropriate privacy, consent, and retention
> policy.

The `main` branch is the hosted Supabase SaaS product. The separate `non-saas`
branch uses its own local deployment design and has not been merged into
`main`.

## Architecture

```text
Teller camera -> FastAPI /upload-face -> DeepFace analysis
                       |                       |
                       `------ Supabase ------'
                                  |
                           Django dashboard
```

Each request supplies a bank code and API key. The Windows computer name is
matched to the longest active PC prefix configured for one of that bank's
branches. Django access is tenant-scoped for platform administrators, bank
administrators, and branch users.

## Quick start

1. Copy `.env.example` to `.env` and enter the Supabase Session pooler values.
2. Install `requirements.txt` in a Python 3.10 virtual environment.
3. Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

All server-side components read the root `.env` file. Password punctuation is
handled safely by the separate `DB_*` settings; no manually assembled database
URL is required.

## Run the system on Windows

Run these setup commands once from the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Fill `.env` with the Django, Supabase, face-analysis, and bank-client values
before continuing. The copy command preserves an existing `.env` file.

Open three PowerShell terminals in the repository root and activate `.venv` in
each terminal.

### Terminal 1: Django dashboard

```powershell
.\.venv\Scripts\Activate.ps1
cd emotion_dashboard
python manage.py migrate
python manage.py runserver 8000
```

Open `http://127.0.0.1:8000/` in your browser.

To create the first platform administrator, run this from the
`emotion_dashboard` directory:

```powershell
python manage.py createsuperuser
```

### Terminal 2: FastAPI face-analysis service

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

The API health check is available at `http://127.0.0.1:8001/health`.

### Terminal 3: Teller camera client

Run the full desktop capture client:

```powershell
.\.venv\Scripts\Activate.ps1
python desktop_capture.py
```

Alternatively, run the smaller reference client:

```powershell
.\.venv\Scripts\Activate.ps1
python clients\device_agent.py
```

Run only one camera client at a time. Its Windows computer name must match an
active branch PC prefix configured in the Django admin.

If an older environment reports that `cv2` has no `CascadeClassifier`, remove
the conflicting OpenCV variants and reinstall the pinned version:

```powershell
python -m pip uninstall -y opencv-python opencv-python-headless
python -m pip install -r requirements.txt
```

### Optional: Docker

After configuring `.env`, Django and FastAPI can instead be started with:

```powershell
docker compose up --build
```

## Main components

- `emotion_dashboard/`: Django SaaS dashboard, admin, tenancy, and migrations.
- `api_server/face_api.py`: bank-authenticated ingestion and analysis API.
- `desktop_capture.py`: production-oriented teller camera client.
- `clients/device_agent.py`: smaller reference camera client.
- `captured_faces/`: private, shared local image storage (gitignored).

## Commercial work remaining

Billing/subscriptions, self-service customer onboarding, private object storage,
audit logs, data export/deletion workflows, production observability, and formal
model/privacy validation remain before a public commercial launch.
