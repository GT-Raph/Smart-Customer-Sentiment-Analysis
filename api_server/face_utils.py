from __future__ import annotations

import cv2
import numpy as np
from scipy.spatial.distance import cosine


def match_face(
    embedding: list[float] | np.ndarray,
    known: list[tuple[int, str, np.ndarray]],
    threshold: float,
) -> tuple[int, str] | None:
    """Return the nearest qualifying visitor rather than the first match."""
    candidate = np.asarray(embedding, dtype=np.float64)
    best: tuple[int, str] | None = None
    best_distance = float("inf")

    for visitor_id, face_id, known_embedding in known:
        if candidate.shape != known_embedding.shape:
            continue
        distance = float(cosine(candidate, known_embedding))
        if np.isnan(distance):
            continue
        if distance < best_distance:
            best_distance = distance
            best = (visitor_id, face_id)

    return best if best is not None and best_distance < threshold else None


def enhance_face(face_img: np.ndarray) -> np.ndarray:
    if face_img is None or face_img.size == 0:
        raise ValueError("Empty face image")
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    return cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
