# Architecture Overview

This document summarizes the core components and data flow for the Facial Emotion Detection and Logging System.

Components
- Folder Watcher
  - Monitors MONITOR_DIR for new image files and enqueues them for processing.
- Processor / Worker
  - Loads image, performs face detection, cropping, and preprocessing.
- Recognition & Emotion Engine
  - Uses DeepFace to compute embeddings and infer emotions.
  - Compares embeddings against stored embeddings (DB or on-disk store) to determine known vs new face.
- Database (MySQL)
  - unique_face_id: stores face_id and serialized/null-serialized embedding
  - emotions: logs each detection with face_id, emotion, confidence, timestamp
- Maintenance Tools
  - Rebuilds known-face store from DB, rotates logs, and performs cleanup.

Data Flow
1. Image arrives in monitored folder.
2. Watcher enqueues image for processing.
3. Processor detects faces, crops, runs DeepFace:
   - Extract embedding
   - Infer emotion with confidence score
4. Identification:
   - Compare embedding to known embeddings (threshold-based cosine/Euclidean)
   - If match found -> use existing face_id; else -> generate new face_id and persist embedding
5. Persist:
   - Write emotion log entry to DB and optionally store face crop on disk (KNOWN_DIR)
6. Consumers:
   - Analytics, dashboards, or downstream services can query /emotions and /faces endpoints.

Resilience and operational considerations
- Idempotence: processing should be idempotent — keep processed-state metadata to avoid duplicates.
- Recovery: stored embeddings allow re-generation of known-face data if disk cache is lost.
- Scaling: for higher throughput, use a queue (Redis/RabbitMQ) and horizontally scale workers.
- Privacy: store only embeddings where possible; avoid storing raw images unless necessary and ensure appropriate retention policies.

Security
- Secure DB credentials, enable least-privilege accounts.
- Audit log access and consider encryption-at-rest for sensitive images or metadata.

Notes
- Model selection (DeepFace backends) affects accuracy and performance. Test backends (VGG-Face, Facenet, ArcFace, etc.) and select for your dataset.
- Tuning thresholds for identification is critical to balance false accepts/rejects.
