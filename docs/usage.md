# Usage and Configuration

This page outlines typical setup and runtime commands for the emotion detection system.

Configuration (environment variables)
- DB_HOST - MySQL host (default: localhost)
- DB_PORT - MySQL port (default: 3306)
- DB_USER - MySQL user
- DB_PASS - MySQL password
- DB_NAME - Database name (default: emotion_detection)
- MONITOR_DIR - Folder to watch for incoming images
- KNOWN_DIR - Folder to store known-face images (optional; can be rebuilt from DB)
- LOG_LEVEL - logging level (INFO/DEBUG)
- GPU_ENABLE - true/false (optional; system will attempt GPU use if true and drivers present)

Quickstart (local)
1. Create virtual environment:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. Install dependencies:
   - pip install -r requirements.txt
3. Configure environment variables (export or .env)
4. Start the monitor script (example):
   - python -m emotion_detection_system.monitor --config ./config.yml
   (Replace with your project's actual entrypoint.)

Submitting a single image (example curl)
- curl -X POST -F "image=@/path/to/img.jpg" http://localhost:5000/api/images

Monitoring and logs
- Check application logs for processing records.
- Health endpoint: GET /api/health

Database migrations and initialization
- Run provided DB init script (if present) to create required tables, or execute the SQL in the README/docs.
- Ensure the DB user has INSERT/SELECT privilege on the emotion_detection DB.

Rebuilding known faces from DB
- If known-face folder is lost, the system can recreate per-face images/embeddings from stored embeddings in unique_face_id.
- Use the provided maintenance script (if available) or a small script that reads embedding, regenerates a representative image, or re-populates the known_face store.

Troubleshooting
- Model download failures: ensure outbound internet or pre-cache models.
- High latency: consider GPU-enabled TensorFlow/PyTorch or reduce frame/image frequency.
- Permission errors on folders: check read/write permissions for MONITOR_DIR and KNOWN_DIR.

Further examples and advanced deployment topics are in docs/ and the project's top-level README.
