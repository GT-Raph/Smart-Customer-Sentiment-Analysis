"""RQ worker task for DeepFace analysis."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import cv2
import ulid

from .config import settings
from .db_utils import (
    complete_snapshot,
    create_visitor,
    get_embeddings,
    get_snapshot,
    mark_failed,
    mark_processing,
)
from .face_utils import enhance_face, match_face

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_deepface():
    from deepface import DeepFace

    return DeepFace


def warm_models() -> None:
    """Download/cache models and keep them warm in this worker process."""
    DeepFace = get_deepface()
    DeepFace.build_model("Emotion", task="facial_attribute")
    if settings.enable_face_identification:
        DeepFace.build_model(settings.embedding_model)


def _normalise_confidence(value: float, vector: dict[str, float]) -> float:
    numeric = float(value)
    total = sum(float(item) for item in vector.values())
    normalised = numeric / 100.0 if total > 1.5 else numeric
    return max(0.0, min(1.0, normalised))


def process_snapshot(snapshot_id: int) -> dict[str, object]:
    """Analyse one snapshot and persist a terminal job status."""
    snapshot = get_snapshot(snapshot_id)
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} does not exist")

    image_path = Path(snapshot["image_path"] or "").resolve()
    try:
        mark_processing(snapshot_id)

        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError("Stored image could not be decoded")

        face_img = enhance_face(frame)

        # Heavy model imports happen only inside worker processes.
        DeepFace = get_deepface()

        analysis = DeepFace.analyze(
            img_path=face_img,
            actions=["emotion"],
            enforce_detection=True,
        )
        if isinstance(analysis, list):
            analysis = analysis[0]

        emotion = str(analysis["dominant_emotion"]).lower()
        vector = {str(k).lower(): float(v) for k, v in analysis["emotion"].items()}
        confidence = _normalise_confidence(vector[emotion], vector)

        embedding: list[float] | None = None
        matched_visitor_id: int | None = None
        face_id: str

        if settings.enable_face_identification:
            representation = DeepFace.represent(
                img_path=face_img,
                model_name=settings.embedding_model,
                enforce_detection=True,
            )
            embedding = list(representation[0]["embedding"])
            matched = match_face(
                embedding,
                get_embeddings(),
                settings.match_threshold,
            )
            if matched:
                matched_visitor_id, face_id = matched
            else:
                face_id = str(ulid.new())
        else:
            # Short-lived device session identity: no cross-visit biometric matching.
            session_id = snapshot.get("session_id") or snapshot["job_id"]
            face_id = f"session-{snapshot['device_id']}-{session_id}"

        visitor_id = matched_visitor_id or create_visitor(face_id)

        retained_path: str | None = (
            None if settings.delete_raw_image_after_processing else str(image_path)
        )
        complete_snapshot(
            snapshot_id=snapshot_id,
            visitor_id=visitor_id,
            emotion=emotion,
            confidence=confidence,
            emotion_vector=vector,
            embedding=embedding,
            image_path=retained_path,
        )

        if settings.delete_raw_image_after_processing:
            try:
                image_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not delete processed image for snapshot %s", snapshot_id)

        return {"snapshot_id": snapshot_id, "status": "processed", "emotion": emotion}

    except Exception as exc:
        logger.exception("Snapshot %s failed", snapshot_id)
        try:
            mark_failed(snapshot_id, exc.__class__.__name__)
        except Exception:
            logger.exception("Could not persist failed state for snapshot %s", snapshot_id)
        raise
