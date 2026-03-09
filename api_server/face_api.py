from fastapi import FastAPI, File, UploadFile, Form, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from typing import Optional
import cv2
import numpy as np
import os
import ulid
import logging
from datetime import datetime

from deepface import DeepFace
from redis import Redis
from rq import Queue

from .config import CAPTURED_FACES_DIR, API_KEY, EMBEDDING_MODEL
from .db_utils import (
    get_db,
    save_snapshot_to_db,
    ensure_tables_exist,
    get_embeddings_db,
)
from .face_utils import match_face_id, enhance_face


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("face_api")


# =====================================================
# FASTAPI APP
# =====================================================

app = FastAPI(title="Bank Face + Emotion API")

os.makedirs(CAPTURED_FACES_DIR, exist_ok=True)


# =====================================================
# REDIS QUEUE
# =====================================================

redis_conn = Redis(host="localhost", port=6379, db=0)
queue = Queue("face_jobs", connection=redis_conn)


# =====================================================
# MODEL PRELOAD
# =====================================================

logger.info("Loading models...")
embedding_model = DeepFace.build_model(EMBEDDING_MODEL)
logger.info("Models loaded")


# =====================================================
# API SECURITY
# =====================================================

async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
):
    if not API_KEY:
        return True

    if x_api_key == API_KEY:
        return True

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        if token == API_KEY:
            return True

    raise HTTPException(status_code=401, detail="Unauthorized")


# =====================================================
# IMAGE SERVING
# =====================================================

@app.get("/images/{filename}")
async def serve_image(filename: str):
    safe_filename = os.path.basename(filename)
    path = os.path.join(CAPTURED_FACES_DIR, safe_filename)

    if os.path.exists(path):
        return FileResponse(path)

    raise HTTPException(status_code=404, detail="Image not found")


# =====================================================
# HEALTH
# =====================================================

@app.get("/")
async def root():
    return {"status": "API running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# =====================================================
# EMOTION DETECTION
# =====================================================

def detect_emotion(face_img):
    result = DeepFace.analyze(
        img_path=face_img,
        actions=["emotion"],
        enforce_detection=False,
    )

    if isinstance(result, list):
        result = result[0]

    emotion = result["dominant_emotion"]
    vector = result["emotion"]
    confidence = vector[emotion]

    return emotion, confidence, vector


# =====================================================
# JOB PROCESSOR
# =====================================================

def process_job(job: dict):
    db = None
    cursor = None

    try:
        db = get_db()
        cursor = db.cursor()

        logger.info(f"Processing job {job['job_id']}")

        frame = cv2.imread(job["image_path"])
        if frame is None:
            raise Exception(f"Could not read image: {job['image_path']}")

        faces = DeepFace.extract_faces(
            img_path=frame,
            enforce_detection=False,
        )

        if not faces:
            raise Exception("No face detected")

        known_embeddings = get_embeddings_db(cursor)

        for face in faces:
            fa = face["facial_area"]
            x, y, w, h = fa["x"], fa["y"], fa["w"], fa["h"]

            face_img = frame[y:y + h, x:x + w]
            face_img = enhance_face(face_img)

            emb = DeepFace.represent(
                img_path=face_img,
                model_name=EMBEDDING_MODEL,
                model=embedding_model,
                enforce_detection=False,
            )

            embedding = emb[0]["embedding"]

            match = match_face_id(embedding, known_embeddings)
            face_id = match if match else str(ulid.new())

            emotion, confidence, vector = detect_emotion(face_img)

            timestamp = datetime.now()

            save_snapshot_to_db(
                db=db,
                face_id=face_id,
                pc_name=job["pc_name"],
                image_path=job["image_path"],
                timestamp=timestamp,
                embedding=embedding,
                emotion=emotion,
                confidence=confidence,
                emotion_vector=vector,
            )

        logger.info(f"Job completed {job['job_id']}")

    except Exception as e:
        logger.error(f"Job failed {job['job_id']}: {str(e)}")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if db is not None:
            db.close()


# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
def startup_event():
    db = None
    try:
        logger.info("Ensuring database tables exist...")
        db = get_db()
        ensure_tables_exist(db)
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise
    finally:
        if db is not None:
            db.close()


# =====================================================
# UPLOAD ENDPOINT
# =====================================================

@app.post("/upload-face")
async def upload_face(
    request: Request,
    file: UploadFile = File(...),
    pc_name: str = Form(...),
    _auth=Depends(verify_api_key),
):
    try:
        data = await file.read()
        arr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        job_id = str(ulid.new())
        filename = f"{job_id}.jpg"
        path = os.path.join(CAPTURED_FACES_DIR, filename)

        saved = cv2.imwrite(path, frame)
        if not saved:
            raise HTTPException(status_code=500, detail="Failed to save image")

        job = {
            "job_id": job_id,
            "pc_name": pc_name,
            "image_path": path,
        }

        queue.enqueue(process_job, job)

        logger.info(f"Job queued {job_id}")

        return {
            "status": "queued",
            "job_id": job_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Processing error")