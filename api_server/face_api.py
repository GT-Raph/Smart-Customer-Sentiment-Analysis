import logging
import threading
from pathlib import Path
from typing import Annotated

import cv2
import numpy as np
import ulid
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from psycopg2.extras import RealDictCursor

from .config import (
    ALLOWED_IMAGE_TYPES,
    CAPTURED_FACES_ROOT,
    EMBEDDING_MODEL,
    MAX_UPLOAD_BYTES,
)
from .db_utils import (
    db_healthcheck,
    get_branch_by_pc_name,
    get_db,
    get_embeddings_db,
    save_snapshot_to_db,
    verify_bank_api_key,
)
from .face_utils import (
    enhance_face,
    match_face_id,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "face_api"
)


FACE_PROCESSING_LOCK = threading.Lock()


app = FastAPI(
    title="Multi-bank Customer Sentiment API",
    version="3.0",
    description=(
        "Automatically assigns each computer to a branch "
        "using its Windows PC name."
    ),
)


def get_deepface():
    """
    Import DeepFace only when image processing is needed.

    This allows the API health endpoint to start even before
    the machine-learning model has been loaded.
    """
    try:
        from deepface import DeepFace

        return DeepFace

    except ImportError as error:
        raise RuntimeError(
            "DeepFace is not installed. Run: "
            "python -m pip install deepface tensorflow"
        ) from error


def authenticate_bank(
    x_bank_code: Annotated[
        str | None,
        Header(),
    ] = None,

    x_api_key: Annotated[
        str | None,
        Header(),
    ] = None,
):
    """
    Authenticate the bank before accepting an image.
    """
    if not x_bank_code or not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "X-Bank-Code and X-API-Key "
                "headers are required."
            ),
        )

    try:
        with get_db() as database:
            with database.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                bank = verify_bank_api_key(
                    cursor,
                    x_bank_code,
                    x_api_key,
                )

    except Exception:
        logger.exception(
            "Bank authentication database error"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is currently unavailable.",
        )

    if not bank:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "The bank code or API key is invalid."
            ),
        )

    return bank


def detect_emotion(
    face_image,
):
    """
    Use DeepFace to determine the dominant emotion.
    """
    DeepFace = get_deepface()

    analysis_result = DeepFace.analyze(
        img_path=face_image,
        actions=["emotion"],
        enforce_detection=False,
    )

    if isinstance(
        analysis_result,
        list,
    ):
        analysis_result = analysis_result[0]

    dominant_emotion = analysis_result[
        "dominant_emotion"
    ]

    raw_emotion_vector = analysis_result[
        "emotion"
    ]

    clean_emotion_vector = {
        str(emotion_name): float(emotion_value)
        for emotion_name, emotion_value
        in raw_emotion_vector.items()
    }

    confidence = float(
        clean_emotion_vector[
            dominant_emotion
        ]
    )

    return (
        dominant_emotion,
        confidence,
        clean_emotion_vector,
    )


def process_face_image(
    frame,
    *,
    job_id,
    bank,
    branch,
    pc_name,
    relative_image_path,
):
    """
    Detect all faces, generate embeddings, match visitors,
    analyse emotions and save the resulting records atomically.
    """
    DeepFace = get_deepface()

    try:
        extracted_faces = DeepFace.extract_faces(
            img_path=frame,
            enforce_detection=True,
        )

    except ValueError as error:
        raise ValueError(
            "No face was detected in the uploaded image."
        ) from error

    if not extracted_faces:
        raise ValueError(
            "No face was detected in the uploaded image."
        )

    with get_db() as database:
        try:
            with database.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                known_embeddings = get_embeddings_db(
                    cursor,
                    bank["id"],
                )

            saved_faces = []

            for face_index, extracted_face in enumerate(
                extracted_faces
            ):
                facial_area = (
                    extracted_face.get(
                        "facial_area"
                    )
                    or {}
                )

                x = max(
                    0,
                    int(
                        facial_area.get(
                            "x",
                            0,
                        )
                    ),
                )

                y = max(
                    0,
                    int(
                        facial_area.get(
                            "y",
                            0,
                        )
                    ),
                )

                width = int(
                    facial_area.get(
                        "w",
                        0,
                    )
                )

                height = int(
                    facial_area.get(
                        "h",
                        0,
                    )
                )

                if width > 0 and height > 0:
                    face_image = frame[
                        y:y + height,
                        x:x + width,
                    ]

                else:
                    face_image = frame

                if face_image.size == 0:
                    continue

                enhanced_face = enhance_face(
                    face_image
                )

                representation_results = DeepFace.represent(
                    img_path=enhanced_face,
                    model_name=EMBEDDING_MODEL,
                    enforce_detection=False,
                )

                if not representation_results:
                    continue

                embedding = representation_results[0][
                    "embedding"
                ]

                matched_face_id = match_face_id(
                    embedding,
                    known_embeddings,
                )

                face_id = (
                    matched_face_id
                    or str(ulid.new())
                )

                (
                    emotion,
                    confidence,
                    emotion_vector,
                ) = detect_emotion(
                    enhanced_face
                )

                snapshot_job_id = (
                    job_id
                    if face_index == 0
                    else f"{job_id}-{face_index}"
                )

                save_snapshot_to_db(
                    database,

                    job_id=snapshot_job_id,

                    bank_id=bank["id"],

                    branch_id=branch["id"],

                    face_id=face_id,

                    pc_name=pc_name,

                    image_path=relative_image_path,

                    embedding=embedding,

                    emotion=emotion,

                    confidence=confidence,

                    emotion_vector=emotion_vector,
                )

                known_embeddings.append(
                    (
                        face_id,

                        np.asarray(
                            embedding,
                            dtype=np.float64,
                        ),
                    )
                )

                saved_faces.append(
                    {
                        "face_id": face_id,
                        "emotion": emotion,
                        "confidence": confidence,
                    }
                )

            if not saved_faces:
                raise ValueError(
                    "The image did not produce a valid face record."
                )

            database.commit()
            return saved_faces

        except Exception:
            database.rollback()
            raise


@app.get("/")
def root():
    return {
        "status": "running",

        "service": (
            "Multi-bank customer sentiment API"
        ),

        "branch_detection": (
            "Automatic through Windows PC name"
        ),
    }


@app.get("/health")
def health():
    try:
        return {
            "status": "ok",
            "database": db_healthcheck(),
        }

    except Exception:
        logger.exception(
            "Health-check database error"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is unavailable.",
        )


@app.post(
    "/upload-face",
    status_code=status.HTTP_201_CREATED,
)
def upload_face(
    file: UploadFile = File(...),

    pc_name: str = Form(
        ...,
        min_length=1,
        max_length=128,
    ),

    bank=Depends(
        authenticate_bank
    ),
):
    """
    Receive an image and automatically determine its branch
    using the supplied Windows computer name.

    The client is not allowed to choose a branch manually.
    """
    normalized_pc_name = (
        pc_name.strip().upper()
    )

    if not normalized_pc_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid Windows computer name is required.",
        )

    if (
        "/" in normalized_pc_name
        or "\\" in normalized_pc_name
        or normalized_pc_name in {".", ".."}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invalid image storage path was generated.",
        )

    if (
        file.content_type
        not in ALLOWED_IMAGE_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Only JPEG, PNG and WebP images "
                "are accepted."
            ),
        )

    uploaded_data = file.file.read(
        MAX_UPLOAD_BYTES + 1
    )

    if len(uploaded_data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The uploaded image is too large.",
        )

    image_array = np.frombuffer(
        uploaded_data,
        np.uint8,
    )

    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image.",
        )

    try:
        with get_db() as database:
            with database.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                branch = get_branch_by_pc_name(
                    cursor,
                    bank["id"],
                    normalized_pc_name,
                )

    except Exception:
        logger.exception(
            "Branch lookup failed for bank=%s pc=%s",
            bank["code"],
            normalized_pc_name,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The database could not determine "
                "the computer's branch."
            ),
        )

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Computer '{normalized_pc_name}' is not "
                f"assigned to any active branch of "
                f"{bank['name']}. "
                "Configure a matching PC prefix in the "
                "branch settings."
            ),
        )

    job_id = str(
        ulid.new()
    )

    relative_image_path = str(
        Path(bank["code"])
        / branch["code"]
        / normalized_pc_name
        / f"{job_id}.jpg"
    )

    absolute_image_path = (
        CAPTURED_FACES_ROOT
        / relative_image_path
    ).resolve()

    if (
        CAPTURED_FACES_ROOT
        not in absolute_image_path.parents
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invalid image storage path was generated.",
        )

    absolute_image_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_saved = cv2.imwrite(
        str(absolute_image_path),
        frame,
    )

    if not image_saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The uploaded image could not be saved.",
        )

    try:
        with FACE_PROCESSING_LOCK:
            processed_faces = process_face_image(
                frame,

                job_id=job_id,

                bank=bank,

                branch=branch,

                pc_name=normalized_pc_name,

                relative_image_path=relative_image_path,
            )

    except ValueError as error:
        absolute_image_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )

    except Exception:
        logger.exception(
            (
                "Face processing failed: "
                "bank=%s branch=%s pc=%s job=%s"
            ),
            bank["code"],
            branch["code"],
            normalized_pc_name,
            job_id,
        )

        absolute_image_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Face and emotion processing failed.",
        )

    return {
        "status": "processed",

        "job_id": job_id,

        "bank": {
            "code": bank["code"],
            "name": bank["name"],
        },

        "branch": {
            "code": branch["code"],
            "name": branch["name"],
            "matched_pc_prefix": (
                branch["matched_prefix"]
            ),
        },

        "pc_name": normalized_pc_name,

        "faces": processed_faces,
    }