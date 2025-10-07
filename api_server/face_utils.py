import numpy as np
import json
from deepface import DeepFace
from scipy.spatial.distance import cosine
import cv2

from .config import EMBEDDING_MODEL, MATCH_THRESHOLD

def get_face_embedding(face_img):
    try:
        reps = DeepFace.represent(face_img, model_name=EMBEDDING_MODEL, enforce_detection=False)
        if reps and isinstance(reps, list):
            emb = reps[0]['embedding']
            return np.array(emb, dtype=np.float64)
    except Exception as e:
        print(f"❌ Embedding error: {e}")
    return None


def match_face_id(embedding, known, threshold=MATCH_THRESHOLD):
    for face_id, known_emb in known:
        dist = cosine(embedding, known_emb)
        if dist < threshold:
            return face_id
    return None


def enhance_face(face_img):
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    return cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
