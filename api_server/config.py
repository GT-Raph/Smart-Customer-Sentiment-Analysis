import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def bounded_int_env(
    name,
    default,
    *,
    minimum,
    maximum,
):
    try:
        value = int(
            os.getenv(
                name,
                str(default),
            )
        )
    except (TypeError, ValueError):
        value = default

    return max(
        minimum,
        min(value, maximum),
    )


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

CAPTURED_FACES_ROOT = Path(
    os.getenv(
        "CAPTURED_FACES_ROOT",
        PROJECT_ROOT / "captured_faces",
    )
).resolve()

CAPTURED_FACES_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "ArcFace",
)

MATCH_THRESHOLD = float(
    os.getenv(
        "MATCH_THRESHOLD",
        "0.45",
    )
)

MAX_UPLOAD_BYTES = int(
    os.getenv(
        "MAX_UPLOAD_BYTES",
        str(5 * 1024 * 1024),
    )
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "connect_timeout": bounded_int_env(
        "DB_CONNECT_TIMEOUT_SECONDS",
        10,
        minimum=1,
        maximum=60,
    ),
    "sslmode": os.getenv(
        "DB_SSLMODE",
        "require",
    ),
}