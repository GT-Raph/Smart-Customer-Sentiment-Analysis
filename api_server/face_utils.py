import cv2
import numpy as np
from scipy.spatial.distance import cosine

from .config import MATCH_THRESHOLD


def match_face_id(
    embedding,
    known_embeddings,
    threshold=MATCH_THRESHOLD,
):
    candidate = np.asarray(
        embedding,
        dtype=np.float64,
    )

    best_face_id = None
    best_distance = float("inf")

    for face_id, known_embedding in known_embeddings:
        distance = cosine(
            candidate,
            np.asarray(
                known_embedding,
                dtype=np.float64,
            ),
        )

        if np.isnan(distance):
            continue

        if distance < best_distance:
            best_distance = distance
            best_face_id = face_id

    if best_distance < threshold:
        return best_face_id

    return None


def enhance_face(face_image):
    gray = cv2.cvtColor(
        face_image,
        cv2.COLOR_BGR2GRAY,
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced_gray = clahe.apply(gray)

    return cv2.cvtColor(
        enhanced_gray,
        cv2.COLOR_GRAY2BGR,
    )