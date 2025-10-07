import os
import socket

# General
CAPTURED_FACES_DIR = os.path.join(os.path.dirname(__file__), "..", "captured_faces")
EMBEDDING_MODEL = "ArcFace"
MATCH_THRESHOLD = 0.45

# MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "emotion_detection"
}

# Local system
PC_NAME = socket.gethostname()

# Ensure directory exists
os.makedirs(CAPTURED_FACES_DIR, exist_ok=True)
