# Facial Emotion Detection and Logging System

This project monitors a folder for facial images, detects emotions, identifies whether a face is new or known, and logs the emotion along with face data into a MySQL database. It uses DeepFace for facial recognition and emotion analysis.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
  - [System](#system)
  - [Python](#python)
  - [Machine Learning / Libraries](#machine-learning--libraries)
  - [Database](#database)
  - [Optional: GPU](#optional-gpu)
- [Quickstart](#quickstart)
- [Architecture Summary](#architecture-summary)
- [Database Schema](#database-schema)
- [Docs](#docs)
- [License](#license)

## 🚀 Features

- Automatic detection of faces from a monitored folder
- Facial emotion recognition (e.g., happy, sad, angry, etc.)
- Embedding-based face identification and unique ID generation
- MySQL database logging of users and their emotions
- Self-healing identification even if known image folder is deleted

## 🛠 Requirements

### System
- Supported OS: Windows 10+, macOS, or Linux.
- Disk: sufficient space for images and model caches.
- Recommended: 8+ GB RAM for CPU inference; more recommended for training/large workloads.

### Python
- Python 3.10.11 recommended.
- Use a virtual environment (venv, pipenv, or conda).

### Machine Learning / Libraries
- Primary ML framework: DeepFace (wraps TensorFlow or PyTorch backends).
- Core packages (defined in requirements.txt):
  - deepface
  - tensorflow (or torch if configured)
  - opencv-python
  - numpy, pandas
  - scikit-learn (optional for downstream processing)
- Install packages with:
  ```bash
  pip install -r requirements.txt
  ```

### Database
- MySQL Server (e.g., standalone MySQL, MariaDB, or XAMPP MySQL).
- Minimum recommended version: MySQL 5.7+ or compatible MariaDB.
- Python connector: mysql-connector-python or PyMySQL (ensure it's listed in requirements.txt).
- Example: configure database connection settings in the project config before first run.

### Optional: GPU (for faster model inference)
- If you plan to use a GPU for inference:
  - NVIDIA GPU with CUDA support.
  - Compatible CUDA toolkit and cuDNN versions for your TensorFlow/PyTorch build.
  - Install GPU-enabled TensorFlow or torch wheels matching your CUDA version.
- Without GPU, CPU-only inference is supported but slower.

## 🚀 Quickstart
1. Clone or download this repository.
2. Create and activate a Python virtual environment:
   - `python -m venv .venv`
   - `source .venv/bin/activate`  (macOS/Linux) or `.venv\Scripts\activate` (Windows)
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Configure database connection and monitored folders (see docs/ for examples).
5. Start the monitoring service/script.

## Architecture Summary
- Input: images dropped into a monitored folder.
- Processing: DeepFace extracts face embeddings and detects emotions.
- Identification: embeddings compared to known-face store; new unique IDs created for unseen faces.
- Storage: face embeddings and emotion logs persisted to MySQL for analytics and reporting.
- Resilience: system can re-generate known-face store from persisted embeddings in DB.

## SQL Database Schema
-- Create the database
CREATE DATABASE IF NOT EXISTS emotion_detection;

-- Use the database
USE emotion_detection;

-- Create users table to store unique faces and embeddings
CREATE TABLE IF NOT EXISTS unique_face_id (
    face_id VARCHAR(255) PRIMARY KEY,
    embedding LONGTEXT NOT NULL
);

-- Create emotions table to log emotion analysis results
CREATE TABLE IF NOT EXISTS emotions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    face_id VARCHAR(255),
    detected_emotion VARCHAR(100),
    confidence FLOAT,
    timestamp DATETIME,
    FOREIGN KEY (face_id) REFERENCES users(face_id)
);


## Docs
- Detailed configuration, deployment, and troubleshooting steps are available in the docs/ directory. Refer to docs/ for DB configuration examples, environment variables, and advanced tuning (GPU setup, model selection, privacy considerations).

## 🚫 Git Ignore (notes)
- The following folders are typically ignored and not tracked by git:
  - emotion_detection_system/captured_faces/
  - emotion_detection_system/known_faces/
  - emotion_detection_system/Process/

## Installation (quick)
1. Clone or download this repo.
2. Install required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

## License
- See LICENSE or project root for license details.