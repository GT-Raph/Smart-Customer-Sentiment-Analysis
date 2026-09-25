from __future__ import annotations

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
