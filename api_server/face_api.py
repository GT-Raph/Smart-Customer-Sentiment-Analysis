from fastapi import FastAPI, File, UploadFile, Form, Depends, Header, HTTPException, status, Request
from fastapi.responses import JSONResponse, FileResponse
import cv2
import numpy as np
import os
from datetime import datetime
import ulid
import json
from deepface import DeepFace

# Safe imports (works as package or standalone)
try:
    from .config import CAPTURED_FACES_DIR, PC_NAME, API_KEY
    from .db_utils import get_db, save_snapshot_to_db, ensure_tables_exist, get_embeddings_db
    from .face_utils import match_face_id, enhance_face
except:
    from config import CAPTURED_FACES_DIR, PC_NAME, API_KEY
    from db_utils import get_db, save_snapshot_to_db, ensure_tables_exist, get_embeddings_db
    from face_utils import match_face_id, enhance_face


app = FastAPI(title="Face Recognition + Emotion API")


# =========================================================
# 🔐 API KEY SECURITY
# =========================================================

async def verify_api_key(
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    if not API_KEY:
        return True

    if x_api_key == API_KEY:
        return True

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        if token == API_KEY:
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized"
    )


# =========================================================
# 📁 DIRECTORY SETUP
# =========================================================

PENDING_JOBS_DIR = os.path.join(CAPTURED_FACES_DIR, "pending_jobs")

os.makedirs(CAPTURED_FACES_DIR, exist_ok=True)
os.makedirs(PENDING_JOBS_DIR, exist_ok=True)


# =========================================================
# 🖼️ IMAGE SERVING
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
# 🚀 MAIN FACE UPLOAD ENDPOINT
# =========================================================

@app.post("/upload-face")
async def upload_face(
    request: Request,
    file: UploadFile = File(...),
    pc_name: str = Form(None),
    _auth=Depends(verify_api_key)
):

    try:
        # --------------------------------------------------
        # 1️⃣ Decode Image
        # --------------------------------------------------
        image_bytes = await file.read()
        np_array = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if frame is None:
            return JSONResponse(
                {"status": "error", "message": "Invalid image"},
                status_code=400
            )

        # --------------------------------------------------
        # 2️⃣ Extract Faces
        # --------------------------------------------------
        faces = DeepFace.extract_faces(
            img_path=frame,
            enforce_detection=False
        )

        if not faces:
            return JSONResponse(
                {"status": "error", "message": "No face detected"},
                status_code=400
            )

        db = get_db()
        ensure_tables_exist(db)

        cursor = db.cursor()
        known_embeddings = get_embeddings_db(cursor)
        cursor.close()

        results = []

        # --------------------------------------------------
        # 3️⃣ Process Each Face
        # --------------------------------------------------
        for face in faces:

            facial_area = face["facial_area"]
            x, y, w, h = (
                facial_area["x"],
                facial_area["y"],
                facial_area["w"],
                facial_area["h"],
            )

            face_img = frame[y:y+h, x:x+w]
            face_img = enhance_face(face_img)

            # --------------------------------------------------
            # 4️⃣ Compute Embedding
            # --------------------------------------------------
            embedding_obj = DeepFace.represent(
                img_path=face_img,
                model_name="Facenet",
                enforce_detection=False
            )

            if not embedding_obj:
                continue

            embedding = embedding_obj[0]["embedding"]

            # --------------------------------------------------
            # 5️⃣ Match Face
            # --------------------------------------------------
            match = match_face_id(embedding, known_embeddings)

            if match:
                face_id = match
                matched = True
            else:
                face_id = str(ulid.new())
                matched = False

            # --------------------------------------------------
            # 6️⃣ Detect Emotion
            # --------------------------------------------------
            emotion_analysis = DeepFace.analyze(
                img_path=face_img,
                actions=["emotion"],
                enforce_detection=False
            )

            emotion = emotion_analysis[0]["dominant_emotion"]

            # --------------------------------------------------
            # 7️⃣ Save Image
            # --------------------------------------------------
            timestamp = datetime.now()
            filename = f"{face_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            image_path = os.path.join(CAPTURED_FACES_DIR, filename)

            cv2.imwrite(image_path, face_img)

            image_url = str(request.url_for("serve_image", filename=filename))

            # --------------------------------------------------
            # 8️⃣ Save to Database
            # --------------------------------------------------
            save_snapshot_to_db(
                db=db,
                face_id=face_id,
                pc_name=pc_name,
                image_path=image_path,
                timestamp=timestamp,
                embedding=embedding,
                emotion=emotion
            )

            # --------------------------------------------------
            # 9️⃣ Create Pending Job JSON
            # --------------------------------------------------
            job_data = {
                "job_id": str(ulid.new()),
                "face_id": face_id,
                "pc_name": pc_name,
                "image_path": image_path,
                "image_url": image_url,
                "emotion": emotion,
                "matched": matched,
                "timestamp": timestamp.isoformat()
            }

            job_filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{face_id}.json"
            job_path = os.path.join(PENDING_JOBS_DIR, job_filename)

            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2)

            results.append({
                "face_id": face_id,
                "matched": matched,
                "emotion": emotion,
                "image_url": image_url
            })

        db.close()

        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        print("API ERROR:", e)
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )
