"""RQ worker task for DeepFace analysis."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import ulid

from .config import settings
from .db_utils import (
    complete_snapshot,
    create_visitor,
    get_embeddings,
    get_recent_session_emotions,
    get_snapshot,
    mark_failed,
    mark_processing,
)
from .face_utils import match_face

logger = logging.getLogger(__name__)

SUPPORTED_EMOTIONS = frozenset(
    {"angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"}
)


@lru_cache(maxsize=1)
def get_deepface():
    from deepface import DeepFace

    return DeepFace


def warm_models() -> None:
    """Download/cache models and keep them warm in this worker process."""
    DeepFace = get_deepface()
    DeepFace.build_model("Emotion", task="facial_attribute")
    if settings.emotion_detector_backend != "skip":
        DeepFace.build_model(
            settings.emotion_detector_backend,
            task="face_detector",
        )
    if settings.enable_face_identification:
        DeepFace.build_model(settings.embedding_model)


class PoorImageQualityError(ValueError):
    """Raised when a face crop is too poor for a meaningful classification."""


def _validate_image_quality(frame: np.ndarray) -> None:
    if frame is None or frame.size == 0:
        raise PoorImageQualityError("Empty face image")

    height, width = frame.shape[:2]
    if min(height, width) < settings.emotion_min_face_size:
        raise PoorImageQualityError("Face image is too small")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    if not settings.emotion_min_brightness <= brightness <= settings.emotion_max_brightness:
        raise PoorImageQualityError("Face image exposure is outside the usable range")

    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if sharpness < settings.emotion_min_sharpness:
        raise PoorImageQualityError("Face image is too blurry")


def _normalise_vector(vector: dict[str, float]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for emotion, score in vector.items():
        label = str(emotion).strip().lower()
        numeric_score = float(score)
        if label in SUPPORTED_EMOTIONS and math.isfinite(numeric_score):
            cleaned[label] = max(0.0, numeric_score)

    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("Emotion model returned an empty probability vector")
    return {emotion: score / total for emotion, score in cleaned.items()}


def _average_vectors(vectors: list[dict[str, float]]) -> dict[str, float]:
    if not vectors:
        raise ValueError("At least one emotion vector is required")

    normalised = [_normalise_vector(vector) for vector in vectors]
    labels = sorted({label for vector in normalised for label in vector})
    averaged = {
        label: sum(vector.get(label, 0.0) for vector in normalised) / len(normalised)
        for label in labels
    }
    return _normalise_vector(averaged)


def _robust_temporal_consensus(
    vectors: list[dict[str, float]],
) -> dict[str, float]:
    """Combine burst frames while limiting the effect of one bad prediction."""
    if not vectors:
        raise ValueError("At least one emotion vector is required")
    if len(vectors) < 3:
        return _average_vectors(vectors)

    normalised = [_normalise_vector(vector) for vector in vectors]
    labels = sorted({label for vector in normalised for label in vector})
    median_vector = {
        label: float(np.median([vector.get(label, 0.0) for vector in normalised]))
        for label in labels
    }
    return _normalise_vector(median_vector)


def _face_area(analysis: dict[str, Any]) -> int:
    region = analysis.get("region") or analysis.get("facial_area") or {}
    try:
        return max(0, int(region.get("w", 0))) * max(0, int(region.get("h", 0)))
    except (AttributeError, TypeError, ValueError):
        return 0


def _select_primary_analysis(result: object) -> dict[str, Any]:
    """Select the largest detected face instead of trusting result ordering."""
    if isinstance(result, dict):
        analyses = [result]
    elif isinstance(result, list):
        analyses = [item for item in result if isinstance(item, dict)]
    else:
        analyses = []

    if not analyses:
        raise ValueError("Emotion model returned no face analysis")
    return max(analyses, key=_face_area)


def _emotion_vector_from_analysis(analysis: dict[str, Any]) -> dict[str, float]:
    vector = analysis.get("emotion")
    if not isinstance(vector, dict):
        raise ValueError("Emotion model returned no probability vector")
    return _normalise_vector(
        {str(key): float(value) for key, value in vector.items()}
    )


def _detected_face_crop(
    frame: np.ndarray,
    analysis: dict[str, Any],
) -> np.ndarray:
    """Return a bounded detected-face crop for post-detection quality checks."""
    region = analysis.get("region") or analysis.get("facial_area")
    if not isinstance(region, dict):
        return frame

    try:
        x = max(0, int(region["x"]))
        y = max(0, int(region["y"]))
        width = max(0, int(region["w"]))
        height = max(0, int(region["h"]))
    except (KeyError, TypeError, ValueError):
        return frame

    x2 = min(frame.shape[1], x + width)
    y2 = min(frame.shape[0], y + height)
    crop = frame[y:y2, x:x2]
    return crop if crop.size else frame


def _deepface_analyze(DeepFace: Any, frame: np.ndarray) -> dict[str, Any]:
    result = DeepFace.analyze(
        img_path=frame,
        actions=["emotion"],
        enforce_detection=True,
        detector_backend=settings.emotion_detector_backend,
        align=True,
        expand_percentage=settings.emotion_expand_percentage,
        silent=True,
    )
    return _select_primary_analysis(result)


def _analyse_emotion_frame(DeepFace: Any, frame: np.ndarray) -> dict[str, float]:
    """Predict one frame, optionally averaging its mirrored prediction."""
    primary = _deepface_analyze(DeepFace, frame)
    _validate_image_quality(_detected_face_crop(frame, primary))
    vectors = [_emotion_vector_from_analysis(primary)]

    if settings.emotion_mirror_ensemble:
        mirrored = np.ascontiguousarray(cv2.flip(frame, 1))
        try:
            mirrored_analysis = _deepface_analyze(DeepFace, mirrored)
            vectors.append(_emotion_vector_from_analysis(mirrored_analysis))
        except Exception as exc:
            # The original view is already valid. A failed optional augmentation
            # should reduce ensemble strength, not discard the whole snapshot.
            logger.warning(
                "Mirrored emotion inference failed; using original view: %s",
                exc.__class__.__name__,
            )

    return _average_vectors(vectors)


def _classify_emotion(
    vector: dict[str, float],
    sample_count: int,
) -> tuple[str, float]:
    ranked = sorted(vector.items(), key=lambda item: item[1], reverse=True)
    emotion, confidence = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = confidence - runner_up

    if (
        sample_count < settings.emotion_min_samples
        or confidence < settings.emotion_min_confidence
        or margin < settings.emotion_min_margin
    ):
        return "uncertain", confidence
    return emotion, confidence


def process_snapshot(snapshot_id: int) -> dict[str, object]:
    """Analyse one snapshot and persist a terminal job status."""
    snapshot = get_snapshot(snapshot_id)
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} does not exist")

    status = str(snapshot.get("status") or "").lower()
    if status == "processed" and bool(snapshot.get("processed")):
        logger.info("Snapshot %s is already processed; skipping duplicate job", snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "status": "processed",
            "emotion": snapshot.get("emotion"),
            "already_complete": True,
        }
    if status == "failed" and snapshot.get("processed_at") is not None:
        logger.info("Snapshot %s already has a terminal failure", snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "status": "failed",
            "reason": snapshot.get("error_message") or "processing_failed",
            "already_complete": True,
        }

    image_path = Path(snapshot["image_path"] or "").resolve()
    try:
        mark_processing(snapshot_id)

        frame = cv2.imread(str(image_path))
        if frame is None:
            raise ValueError("Stored image could not be decoded")

        _validate_image_quality(frame)

        # Heavy model imports happen only inside worker processes.
        DeepFace = get_deepface()

        raw_vector = _analyse_emotion_frame(DeepFace, frame)

        captured_at = snapshot.get("timestamp")
        if not isinstance(captured_at, datetime):
            captured_at = datetime.now(timezone.utc).replace(tzinfo=None)
        recent_emotions = get_recent_session_emotions(
            snapshot_id=snapshot_id,
            device_id=int(snapshot["device_id"]),
            session_id=str(snapshot.get("session_id") or ""),
            captured_at=captured_at,
            window_seconds=settings.emotion_smoothing_window_seconds,
            limit=max(0, settings.emotion_smoothing_frames - 1),
        )
        combined_vector = _robust_temporal_consensus(
            [raw_vector, *(vector for _, vector in recent_emotions)]
        )
        emotion, confidence = _classify_emotion(
            combined_vector,
            sample_count=1 + len(recent_emotions),
        )
        ranked = sorted(combined_vector.values(), reverse=True)
        runner_up = ranked[1] if len(ranked) > 1 else 0.0
        logger.info(
            "Snapshot %s expression=%s confidence=%.3f margin=%.3f samples=%s",
            snapshot_id,
            emotion,
            confidence,
            confidence - runner_up,
            1 + len(recent_emotions),
        )

        embedding: list[float] | None = None
        matched_visitor_id: int | None = None
        face_id: str

        if settings.enable_face_identification:
            representation = DeepFace.represent(
                img_path=frame,
                model_name=settings.embedding_model,
                enforce_detection=True,
                detector_backend=settings.emotion_detector_backend,
                align=True,
                expand_percentage=settings.emotion_expand_percentage,
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
            # Preserve the raw per-frame vector so later burst frames can form
            # an exact average rather than averaging averages.
            emotion_vector=raw_vector,
            embedding=embedding,
            image_path=retained_path,
            consensus_snapshot_ids=[item[0] for item in recent_emotions],
        )

        if settings.delete_raw_image_after_processing:
            try:
                image_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not delete processed image for snapshot %s", snapshot_id)

        return {"snapshot_id": snapshot_id, "status": "processed", "emotion": emotion}

    except PoorImageQualityError:
        logger.info("Snapshot %s rejected because image quality was too low", snapshot_id)
        mark_failed(snapshot_id, "PoorImageQuality")
        if settings.delete_raw_image_after_processing:
            try:
                image_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not delete rejected image for snapshot %s", snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "status": "rejected",
            "reason": "poor_image_quality",
        }

    except Exception as exc:
        logger.exception("Snapshot %s failed", snapshot_id)
        try:
            mark_failed(snapshot_id, exc.__class__.__name__)
        except Exception:
            logger.exception("Could not persist failed state for snapshot %s", snapshot_id)
        if settings.delete_raw_image_after_processing:
            try:
                image_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not delete failed image for snapshot %s", snapshot_id)
        raise
