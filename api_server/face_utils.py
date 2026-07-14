import cv2
import numpy as np

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

    if (
        candidate.ndim != 1
        or candidate.size == 0
    ):
        return None

    candidate_norm = np.linalg.norm(
        candidate
    )

    if (
        not np.isfinite(candidate_norm)
        or candidate_norm == 0
    ):
        return None

    face_ids = []
    compatible_embeddings = []

    for face_id, known_embedding in known_embeddings:
        known_array = np.asarray(
            known_embedding,
            dtype=np.float64,
        )

        if (
            known_array.ndim != 1
            or known_array.shape != candidate.shape
        ):
            continue

        face_ids.append(
            face_id
        )

        compatible_embeddings.append(
            known_array
        )

    if not compatible_embeddings:
        return None

    embedding_matrix = np.vstack(
        compatible_embeddings
    )

    known_norms = np.linalg.norm(
        embedding_matrix,
        axis=1,
    )

    denominators = (
        known_norms * candidate_norm
    )

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        similarities = (
            embedding_matrix @ candidate
        ) / denominators

        distances = 1.0 - np.clip(
            similarities,
            -1.0,
            1.0,
        )

    valid_indices = np.flatnonzero(
        np.isfinite(distances)
    )

    if valid_indices.size == 0:
        return None

    best_index = valid_indices[
        np.argmin(
            distances[valid_indices]
        )
    ]

    if distances[best_index] < threshold:
        return face_ids[
            int(best_index)
        ]

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

    enhanced_gray = clahe.apply(
        gray
    )

    return cv2.cvtColor(
        enhanced_gray,
        cv2.COLOR_GRAY2BGR,
    )