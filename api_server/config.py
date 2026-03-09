import os
import socket

# -------------------------------------------------
# DIRECTORIES
# -------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CAPTURED_FACES_DIR = os.getenv(
    "CAPTURED_FACES_DIR",
    os.path.join(BASE_DIR, "..", "captured_faces")
)

os.makedirs(CAPTURED_FACES_DIR, exist_ok=True)


# -------------------------------------------------
# API SECURITY
# -------------------------------------------------

API_KEY_HEADER = "X-API-Key"

# Read API key from environment variable
API_KEY = os.getenv("FACE_API_KEY")


# -------------------------------------------------
# FACE RECOGNITION SETTINGS
# -------------------------------------------------

EMBEDDING_MODEL = "ArcFace"
MATCH_THRESHOLD = 0.45


# -------------------------------------------------
# DATABASE CONFIG
# (Better to use environment variables in production)
# -------------------------------------------------

# DB_CONFIG = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.getenv("DB_NAME", "postgres"),
#         "USER": os.getenv("DB_USER", ""),
#         "PASSWORD": os.getenv("DB_PASSWORD"),
#         "HOST": os.getenv("DB_HOST", ""),
#         "PORT": os.getenv("DB_PORT", "5432"),
#         "OPTIONS": {
#             "sslmode": "require"
#         },
#     }
# }

DB_CONFIG = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres.uqkodzbevzooiqdxnfjq",
        "PASSWORD": "Z9/Fu*nC$mNTs/+",
        "HOST": "aws-1-eu-central-1.pooler.supabase.com",
        "PORT": "5432",
        "OPTIONS": {
            "sslmode": "require"
        },
    }
}

# -------------------------------------------------
# SYSTEM INFO
# -------------------------------------------------

PC_NAME = socket.gethostname()
