from fastapi import FastAPI, File, UploadFile, Form, Depends, Header, HTTPException, status, Request
from fastapi.responses import JSONResponse, FileResponse
import cv2
import numpy as np
import os
from datetime import datetime
import ulid
from deepface import DeepFace
import json  # added for logging

# Replace strict relative imports with a tolerant try/except so the module can be run
# as a package or as a top-level module (uvicorn face_api:app).
try:
    # preferred when the module is part of a package
    from .config import CAPTURED_FACES_DIR, PC_NAME
    from .db_utils import get_db, get_embeddings_db, save_snapshot_to_db
    from .face_utils import get_face_embedding, match_face_id, enhance_face
except Exception:
    # fallback when running the file as a top-level module (common with uvicorn)
    from config import CAPTURED_FACES_DIR, PC_NAME
    from db_utils import get_db, get_embeddings_db, save_snapshot_to_db
    from face_utils import get_face_embedding, match_face_id, enhance_face

# Load API key from config (if provided) or environment variable
CONFIG_API_KEY = None
try:
    # attempt to import API_KEY from package config if present
    from .config import API_KEY as CONFIG_API_KEY  # type: ignore
except Exception:
    try:
        from config import API_KEY as CONFIG_API_KEY  # type: ignore
    except Exception:
        CONFIG_API_KEY = None

# New: default API key (replace this value with a secure key or set API_KEY in config.py / env)
DEFAULT_API_KEY = "replace-me-with-a-secure-key"

API_KEY = CONFIG_API_KEY or os.getenv("API_KEY") or DEFAULT_API_KEY

if API_KEY == DEFAULT_API_KEY:
    # Warn at startup that the API is running with the built-in default key
    print("⚠️ Using built-in DEFAULT API_KEY. Replace it by setting API_KEY in config.py or the environment for security.")
else:
    # Indicate key source without printing the secret
    src = "config.py" if CONFIG_API_KEY else "environment"
    print(f"✅ API_KEY loaded from {src}. /upload-face is protected.")

# New: pending jobs directory where the API writes JSON "tasks" for processing
PENDING_JOBS_DIR = os.path.join(CAPTURED_FACES_DIR, "pending_jobs")

def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

# ensure captured faces and pending dir exist at startup
_ensure_dir(CAPTURED_FACES_DIR)
_ensure_dir(PENDING_JOBS_DIR)

# Dependency to verify API key (accepts X-API-Key or Authorization: Bearer <token>)
async def verify_api_key(x_api_key: str = Header(None), authorization: str = Header(None)):
    # If API_KEY not configured, allow (no-op)
    if not API_KEY:
        return True
    # Check X-API-Key header first
    if x_api_key and x_api_key == API_KEY:
        return True
    # Fallback to Authorization: Bearer <token>
    if authorization:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]
            if token == API_KEY:
                return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

app = FastAPI(title="Face Recognition API")

# New: serve saved images (safe path check to prevent traversal)
@app.get("/images/{filename}", name="serve_image")
async def serve_image(filename: str):
    # serve files from either CAPTURED_FACES_DIR or PENDING_JOBS_DIR (safe checks)
    safe_name = os.path.basename(filename)
    candidates = [
        os.path.abspath(os.path.join(PENDING_JOBS_DIR, safe_name)),
        os.path.abspath(os.path.join(CAPTURED_FACES_DIR, safe_name))
    ]
    allowed_dirs = [os.path.abspath(PENDING_JOBS_DIR), os.path.abspath(CAPTURED_FACES_DIR)]
    for file_path in candidates:
        # prevent traversal and ensure file lies in one of the allowed dirs
        if any(file_path.startswith(d + os.sep) or file_path == d for d in allowed_dirs):
            if os.path.exists(file_path):
                return FileResponse(path=file_path, media_type="image/jpeg", filename=safe_name)
    raise HTTPException(status_code=404, detail="Not found")

# New: lightweight health endpoint for pre-flight checks
@app.get("/health")
async def health():
    return {"status": "ok"}

# Protect upload-face with the API key dependency
@app.post("/upload-face")
async def upload_face(request: Request, file: UploadFile = File(...), pc_name: str = Form(default=PC_NAME), _auth=Depends(verify_api_key)):
    try:
        # Decode the uploaded image
        image_data = await file.read()
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        db = get_db()
        cursor = db.cursor()
        known = get_embeddings_db(cursor)
        cursor.close()

        faces = DeepFace.extract_faces(frame, enforce_detection=False)
        if not faces:
            return JSONResponse({"status": "error", "message": "No face detected."}, status_code=400)

        results = []
        for face in faces:
            # ...existing face extraction/processing...
            area = face['facial_area']
            x, y, w, h = area['x'], area['y'], area['w'], area['h']
            pad_y, pad_x = int(h * 0.6), int(w * 0.4)
            x1, y1 = max(0, x - pad_x), max(0, y - pad_y)
            x2, y2 = min(frame.shape[1], x + w + pad_x), min(frame.shape[0], y + h + pad_y)
            face_img = frame[y1:y2, x1:x2]

            face_img_clahe = enhance_face(face_img)
            embedding = get_face_embedding(face_img_clahe)
            if embedding is None:
                continue

            matched_id = match_face_id(embedding, known)
            if matched_id:
                face_id, matched, msg = matched_id, True, "Matched existing face_id"
            else:
                face_id, matched, msg = str(ulid.new()), False, "New face detected"

            timestamp = datetime.now()
            filename = f"{face_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"

            # Save image into the PENDING_JOBS_DIR (per request)
            path = os.path.join(PENDING_JOBS_DIR, filename)
            try:
                cv2.imwrite(path, face_img_clahe)
            except Exception as e:
                fallback_path = os.path.join(CAPTURED_FACES_DIR, filename)
                cv2.imwrite(fallback_path, face_img_clahe)
                path = fallback_path

            # Build an accessible image URL (relative to this server)
            try:
                image_url = request.url_for("serve_image", filename=filename)
            except Exception:
                image_url = f"/images/{filename}"
            try:
                image_url = str(image_url)
            except Exception:
                image_url = f"/images/{filename}"

            # Save to DB (path refers to pending_jobs location)
            save_snapshot_to_db(db, face_id, pc_name, path, timestamp, embedding)

            # Write received_images.log with image_url and path
            try:
                log_entry = {
                    "timestamp": timestamp.isoformat(),
                    "pc_name": pc_name,
                    "face_id": face_id,
                    "matched": bool(matched),
                    "image_path": path,
                    "image_url": image_url
                }
                with open("received_images.log", "a", encoding="utf-8") as lf:
                    lf.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as log_e:
                print(f"⚠️ Failed to write received_images.log: {log_e}")

            # Create job JSON in pending_jobs (image_path references file in pending_jobs)
            try:
                job = {
                    "job_id": str(ulid.new()),
                    "face_id": face_id,
                    "pc_name": pc_name,
                    "image_path": path,
                    "image_url": image_url,
                    "timestamp": timestamp.isoformat(),
                    "embedding_saved": embedding is not None
                }
                job_filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{face_id}.json"
                job_path = os.path.join(PENDING_JOBS_DIR, job_filename)
                with open(job_path, "w", encoding="utf-8") as jf:
                    json.dump(job, jf, ensure_ascii=False)
            except Exception as job_e:
                print(f"⚠️ Failed to write pending job file: {job_e}")
                job_path = None

            results.append({
                "face_id": face_id,
                "matched": matched,
                "message": msg,
                "image_path": path,
                "image_url": image_url,
                "job_file": job_path
            })

        db.close()
        return {"status": "success", "results": results}

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
