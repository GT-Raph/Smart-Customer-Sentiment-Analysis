# Development usage

Python 3.10 is recommended for the pinned TensorFlow and DeepFace versions.

## Install

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with the Supabase Session pooler details, Django settings, and bank
client credentials. Both server processes read this root file.

## Run the services

Start Django in one terminal:

```powershell
cd emotion_dashboard
python manage.py migrate
python manage.py runserver 8000
```

Start FastAPI from the repository root in a second terminal:

```powershell
python -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

Start the teller camera client from the repository root in a third terminal:

```powershell
python desktop_capture.py
```

The client connects only to FastAPI. It does not receive or require Supabase
credentials when deployed to a teller machine; use a client-only `.env` there
containing `FACE_API_URL`, `BANK_CODE`, `BANK_API_KEY`, and capture settings.

## Tests

```powershell
python -m unittest discover -s tests -v
cd emotion_dashboard
python manage.py makemigrations --check --dry-run
python manage.py test monitor -v 2
```

The unit tests mock database calls. Django tests use SQLite in CI so they do not
modify hosted tenant data.
