from fastapi import FastAPI, File, UploadFile, Form, Depends, Header, HTTPException, status, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.concurrency import run_in_threadpool
import cv2
import numpy as np
import os
import ulid
import logging
import json
from datetime import datetime
from deepface import DeepFace
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Safe imports
try:
    from .config import CAPTURED_FACES_DIR, API_KEY
    from .db_utils import (
        get_db,
        save_snapshot_to_db,
        ensure_tables_exist,
        get_embeddings_db,
        create_processing_job,
        fetch_unprocessed_jobs,
        mark_job_completed,
        mark_job_failed
    )
    from .face_utils import match_face_id, enhance_face
except:
    from config import CAPTURED_FACES_DIR, API_KEY
    from db_utils import (
        get_db,
        save_snapshot_to_db,
        ensure_tables_exist,
        get_embeddings_db,
        create_processing_job,
        fetch_unprocessed_jobs,
        mark_job_completed,
        mark_job_failed
    )
    from face_utils import match_face_id, enhance_face


# =========================================================
# 🏦 STRUCTURED LOGGING (BANK AUDIT READY)
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("face_api")


# =========================================================
# 🚀 APP INIT
# =========================================================

app = FastAPI(title="Bank Face Recognition + Emotion API")

os.makedirs(CAPTURED_FACES_DIR, exist_ok=True)

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=4)

# =========================================================
# 🧠 PRELOAD MODELS (CRITICAL FOR PERFORMANCE)
# =========================================================

logger.info("Loading DeepFace models...")

emotion_model = DeepFace.build_model("Emotion")
embedding_model = DeepFace.build_model("Facenet")

logger.info("Models loaded successfully.")


# =========================================================
# 🔐 API KEY SECURITY
# =========================================================

async def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    if not API_KEY:
        return True

    if x_api_key == API_KEY:
        return True

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        if token == API_KEY:
            return True

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# =========================================================
# 📁 IMAGE SERVING
# =========================================================

@app.get("/images/{filename}", name="serve_image")
async def serve_image(filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(CAPTURED_FACES_DIR, safe_name)

    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Image not found")


# =========================================================
# ❤️ HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():
    return {"status": "ok"}


# =========================================================
# 🧵 BACKGROUND PROCESSING
# =========================================================

def process_job(job):
    db = get_db()
    cursor = db.cursor()

    try:
        logger.info(f"Processing job {job['job_id']}")

        image_path = job["image_path"]
        pc_name = job["pc_name"]

        frame = cv2.imread(image_path)
        if frame is None:
            raise Exception("Invalid image during processing")

        faces = DeepFace.extract_faces(
            img_path=frame,
            enforce_detection=False
        )

        if not faces:
            raise Exception("No face detected")

        known_embeddings = get_embeddings_db(cursor)

        for face in faces:
            facial_area = face["facial_area"]
            x, y, w, h = facial_area["x"], facial_area["y"], facial_area["w"], facial_area["h"]

            face_img = frame[y:y+h, x:x+w]
            face_img = enhance_face(face_img)

            # Embedding
            embedding_obj = DeepFace.represent(
                img_path=face_img,
                model_name="Facenet",
                model=embedding_model,
                enforce_detection=False
            )

            embedding = embedding_obj[0]["embedding"]

            match = match_face_id(embedding, known_embeddings)

            face_id = match if match else str(ulid.new())

            # Emotion
            emotion_result = DeepFace.analyze(
                img_path=face_img,
                actions=["emotion"],
                models={"emotion": emotion_model},
                enforce_detection=False
            )

            emotion = emotion_result[0]["dominant_emotion"]
            confidence = emotion_result[0]["emotion"][emotion]

            timestamp = datetime.now()

            save_snapshot_to_db(
                db=db,
                face_id=face_id,
                pc_name=pc_name,
                image_path=image_path,
                timestamp=timestamp,
                embedding=embedding,
                emotion=emotion,
                confidence=confidence
            )

        mark_job_completed(db, job["job_id"])
        logger.info(f"Job {job['job_id']} completed")

    except Exception as e:
        logger.error(f"Job {job['job_id']} failed: {str(e)}")
        mark_job_failed(db, job["job_id"], str(e))

    finally:
        cursor.close()
        db.close()


# =========================================================
# 🚀 UPLOAD ENDPOINT (FAST RESPONSE)
# =========================================================

@app.post("/upload-face")
async def upload_face(
    request: Request,
    file: UploadFile = File(...),
    pc_name: str = Form(...),
    _auth=Depends(verify_api_key)
):

    try:
        image_bytes = await file.read()
        np_array = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        job_id = str(ulid.new())
        timestamp = datetime.now()

        filename = f"{job_id}.jpg"
        image_path = os.path.join(CAPTURED_FACES_DIR, filename)

        cv2.imwrite(image_path, frame)

        db = get_db()
        ensure_tables_exist(db)

        create_processing_job(
            db=db,
            job_id=job_id,
            pc_name=pc_name,
            image_path=image_path,
            timestamp=timestamp
        )

        db.close()

        # Submit to background thread
        executor.submit(process_job, {
            "job_id": job_id,
            "pc_name": pc_name,
            "image_path": image_path
        })

        logger.info(f"Job {job_id} accepted from {pc_name}")

        return {
            "status": "accepted",
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Processing error")
