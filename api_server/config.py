import os
import socket
from flask import session

# General
CAPTURED_FACES_DIR = os.path.join(os.path.dirname(__file__), "..", "captured_faces")
EMBEDDING_MODEL = "ArcFace"
MATCH_THRESHOLD = 0.45

API_KEY_HEADER = "X-API-Key"
API_KEY = os.getenv("API_KEY", None)

# PostgreSQL
DB_CONFIG = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres.uqkodzbevzooiqdxnfjq",
        "PASSWORD": "Z9/Fu*nC$mNTs/+",
        "HOST": "aws-1-eu-central-1.pooler.supabase.com",
        "PORT": "5432",
        "OPTIONS": {
            "pool_mode": "session",
            "sslmode": "require",
        },
    }
}

# Local system
PC_NAME = socket.gethostname()

# Ensure directory exists
os.makedirs(CAPTURED_FACES_DIR, exist_ok=True)
