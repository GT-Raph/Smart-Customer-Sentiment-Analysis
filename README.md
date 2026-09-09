# Smart Customer Sentiment Analysis

A self-hosted, non-SaaS application for privacy-conscious facial-expression
analytics. A registered camera device sends a cropped face to the ingestion API,
analysis runs in a background worker, and authorized staff view aggregate results
in the Django dashboard.

> The output is a facial-expression signal, not proof of a person's true
> emotion. Face identification is disabled by default.

## Non-SaaS design

This branch is designed for one organization to operate on its own infrastructure.
It has no customer tenants, plans, subscriptions, billing records, or monthly usage
quotas. Branches represent the organization's physical locations and are retained
for access control and comparison reports.

Device API keys, authenticated dashboard users, upload limits, and privacy controls
remain in place because they are security features rather than SaaS features.
The dashboard templates, navigation, analytics pages, charts, branding, and
responsive styling intentionally retain the SaaS edition's user experience.

## Architecture

```text
Camera agent -> FastAPI ingestion -> XAMPP MariaDB + Redis queue
                                           |
                                           v
                                  DeepFace RQ worker
                                           |
                                           v
                                   Django dashboard
```

## Quick start

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). If migrating a database created by
the SaaS branch, read [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) first.

## Run the system on Windows

Use Python 3.10 and run all commands below from the repository root. Start
**MySQL** in the XAMPP Control Panel first. Copy the environment template once,
then review `.env` before continuing:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

If XAMPP reports MariaDB 10.4, keep this compatibility setting enabled in
`.env`:

```dotenv
XAMPP_ALLOW_MARIADB_10_4=true
```

### One-time database setup

Create the `smart_sentiment` database in phpMyAdmin as described in the
deployment guide, then run:

```powershell
.\.venv\Scripts\python.exe emotion_dashboard\manage.py migrate
.\.venv\Scripts\python.exe emotion_dashboard\manage.py createsuperuser
```

Sign in to `http://127.0.0.1:8000/admin/` after starting Django and create a
branch. The branch ID is the number in its admin page URL. Then generate a
camera key using that actual ID (the example below uses `2`):

```powershell
$branchId = 2
.\.venv\Scripts\python.exe emotion_dashboard\manage.py create_device_key --branch $branchId --name front-desk-camera --pc-name ACCRA01-CAMERA
```

Copy the generated key into `DEVICE_API_KEY` in `.env`. The key is displayed
only once.

### Start Redis

Redis handles the background processing queue. Start Docker Desktop and wait
until it reports that the engine is running. Then run:

```powershell
docker compose --env-file .compose.env up -d redis
```

The separate `.compose.env` file prevents Docker Compose from interpreting
dollar signs in application passwords. The containers still read the real
application settings from `.env`.

### Terminal 1: Django dashboard

```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe emotion_dashboard\manage.py runserver 8000
```

Open `http://127.0.0.1:8000/`.

### Terminal 2: FastAPI ingestion service

```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

### Terminal 3: DeepFace worker

Create the worker environment once because its machine-learning dependencies
are intentionally separate from the web environment:

```powershell
py -3.10 -m venv .venv-worker
.\.venv-worker\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r api_server\requirements-worker.txt
.\.venv-worker\Scripts\python.exe -m api_server.worker_main
```

On later starts, activate `.venv-worker` and run only the final command.

### Terminal 4: Camera client

The camera client has no live preview. It appears only as a Sentiment Grid icon
in the Windows notification area. For each sample it opens the camera briefly,
captures one frame, and releases the camera before processing or uploading. If
another application is using the camera, the agent backs off and retries
automatically.

Start it in the foreground once to confirm its configuration:

```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe clients\device_agent.py
```

Right-click the tray icon to pause for 15 minutes, 30 minutes, one hour, or
until the configured end of shift. Pauses expire automatically and survive an
agent or computer restart. The agent sends a notification shortly before
capture resumes. There is intentionally no permanent teller-level pause.

After verifying it, stop the foreground agent with `Ctrl+C`, then start the tray
agent without a console window:

```powershell
Start-Process -FilePath ".\.venv\Scripts\pythonw.exe" -ArgumentList "clients\device_agent.py" -WorkingDirectory (Get-Location)
```

Administrators can also control the same finite pause lease from PowerShell:

```powershell
.\.venv\Scripts\python.exe clients\device_agent.py --pause 30 --reason "Customer video call"
.\.venv\Scripts\python.exe clients\device_agent.py --status
.\.venv\Scripts\python.exe clients\device_agent.py --resume
```

For console-only troubleshooting, use `--no-tray`. The tray status changes to
**Camera busy** while another application owns the camera and returns to
**Active** after the camera becomes available.

Keep XAMPP MySQL, Redis, Django, FastAPI, and the worker running while using the
camera client. Stop a foreground service with `Ctrl+C`. Stop Redis when finished
with:

```powershell
docker compose --env-file .compose.env stop redis
```

## Main services

- `emotion_dashboard/`: local administration and analytics dashboard.
- `api_server/face_api.py`: authenticated image-ingestion API.
- `api_server/worker.py`: DeepFace/RQ inference worker.
- `clients/device_agent.py`: low-rate reference camera client.
