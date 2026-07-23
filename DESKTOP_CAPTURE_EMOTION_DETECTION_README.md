# Smart Customer Sentiment Analysis
## Desktop Capture & Emotion Detection Developer README

This README is for a developer helping with the **Desktop Capture / Emotion Detection** side of the Smart Customer Sentiment Analysis system.

The system is designed for bank teller workstations. A customer-facing camera watches the normal customer position, selects a usable face image, and sends it to a central FastAPI service. The API identifies the bank and branch, performs face embedding/matching and emotion analysis, stores the result, and makes it available in the Django dashboard.

---

## 1. System Overview

```text
Customer
   |
   v
Customer-facing camera at teller workstation
   |
   v
desktop_capture.py
   |
   |-- Detects a face locally
   |-- Restricts detection to a customer capture zone
   |-- Rejects poor-quality frames
   |-- Checks blur / brightness / face size
   |-- Waits for a stable face
   |-- Selects the best frame
   |-- Prevents repeated captures during one interaction
   |-- Queues retryable uploads when the API is unavailable
   |
   v
FastAPI Face/Emotion API - port 8001
   |
   |-- Authenticates the bank
   |-- Reads the Windows PC name
   |-- Determines the branch from the configured PC prefix
   |-- Saves the image safely
   |-- Extracts the face
   |-- Generates a face embedding
   |-- Matches an existing visitor or creates a new Face ID
   |-- Runs emotion analysis
   |-- Saves the result atomically
   |
   v
PostgreSQL
   |
   v
Django Dashboard - port 8000
```

The main files relevant to the emotion-detection developer are:

```text
desktop_capture.py
api_server/face_api.py
api_server/face_utils.py
api_server/config.py
api_server/db_utils.py
```

The most important file for camera behaviour is:

```text
desktop_capture.py
```

---

## 2. Main Design Goal

Customers should **not have to pose for the camera**.

The system should work while the customer behaves normally at the teller counter.

The desktop client should automatically decide:

- whether exactly one usable customer face is visible;
- whether the face is large enough;
- whether the image is blurred;
- whether the face is too dark or overexposed;
- whether the face has remained stable long enough;
- which candidate frame is the best;
- whether the current customer has already been captured.

The desktop client should **not upload every frame**.

---

## 3. Expected Project Structure

```text
Smart-Customer-Sentiment-Analysis/
|
|-- api_server/
|   |-- __init__.py
|   |-- config.py
|   |-- db_utils.py
|   |-- face_api.py
|   |-- face_utils.py
|
|-- emotion_dashboard/
|   |-- manage.py
|   |-- emotion_dashboard/
|   |-- monitor/
|
|-- emotion_detection_system/
|   |-- desktop_capture.ipynb
|
|-- desktop_capture.py
|-- requirements.txt
|-- .env
|-- .venv/
|-- offline_queue/
|-- captured_faces/
```

The root-level `desktop_capture.py` is the production teller-workstation capture client.

The notebook under `emotion_detection_system/desktop_capture.ipynb` is for experimentation only.

---

## 4. Technologies Used

Main technologies:

```text
Python
OpenCV
FastAPI
Uvicorn
DeepFace
TensorFlow
TF-Keras
NumPy
Requests
PostgreSQL
Django
```

The most important emotion/capture packages are:

```text
opencv-python
deepface
tensorflow
tf-keras
numpy
requests
python-dotenv
```

---

## 5. Security Rules Before Development

Never commit:

```text
.env
API keys
database passwords
captured customer images
offline queue images
virtual environments
```

Recommended `.gitignore` entries:

```gitignore
.env
.venv/
venv/
__pycache__/
*.pyc
captured_faces/
offline_queue/
db.sqlite3
.ipynb_checkpoints/
```

Treat facial images and embeddings as sensitive data.

Use consenting test participants during development.

---

## 6. Windows Setup

Open PowerShell and move into the project:

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
```

Create a virtual environment if needed:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Upgrade packaging tools:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

Install project requirements:

```powershell
python -m pip install -r requirements.txt
```

If any capture/emotion packages are missing:

```powershell
python -m pip install opencv-python numpy requests python-dotenv
python -m pip install deepface tensorflow tf-keras
```

Do not randomly upgrade ML packages on a working environment. First record the current environment:

```powershell
python -m pip freeze > current_environment.txt
```

---

## 7. Verify OpenCV

Run:

```powershell
python -c "import cv2; print('OpenCV:', cv2.__version__); print('CascadeClassifier:', hasattr(cv2, 'CascadeClassifier'))"
```

Expected:

```text
CascadeClassifier: True
```

Check installed OpenCV packages:

```powershell
python -m pip list | findstr opencv
```

Avoid conflicting OpenCV variants.

---

## 8. Verify TensorFlow, TF-Keras and DeepFace

Run:

```powershell
python -c "import tensorflow as tf; import tf_keras; print('TensorFlow:', tf.__version__); print('TF-Keras:', tf_keras.__version__)"
```

Then:

```powershell
python -c "from deepface import DeepFace; print('DeepFace imported successfully')"
```

If DeepFace reports a TensorFlow/TF-Keras compatibility problem, fix that dependency issue before debugging the camera.

---

## 9. `.env` Configuration

Create `.env` in the project root.

Example:

```env
FACE_API_URL=http://127.0.0.1:8001/upload-face

BANK_CODE=FIDELITY_GH
BANK_API_KEY=PASTE_THE_BANK_API_KEY_HERE

CAMERA_INDEX=0
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FPS=30

REQUEST_TIMEOUT_SECONDS=90

PREVIEW_ENABLED=true
UPLOAD_FACE_CROP=true
JPEG_QUALITY=92

ROI_LEFT=0.18
ROI_TOP=0.06
ROI_RIGHT=0.82
ROI_BOTTOM=0.96

MIN_FACE_WIDTH_PIXELS=120
MIN_FACE_HEIGHT_PIXELS=120
MIN_FACE_AREA_RATIO=0.035

BLUR_THRESHOLD=45

MIN_BRIGHTNESS=45
MAX_BRIGHTNESS=215

MAX_DARK_PIXEL_PERCENT=0.58
MAX_BRIGHT_PIXEL_PERCENT=0.38

STABLE_FRAMES_REQUIRED=6
STABILITY_IOU_THRESHOLD=0.55

SAMPLE_WINDOW_SECONDS=1.2
MIN_GOOD_CANDIDATES=4
DETECTION_INTERVAL_FRAMES=2

FACE_ABSENCE_RESET_SECONDS=1.8
CAPTURE_COOLDOWN_SECONDS=5

OFFLINE_QUEUE_DIR=offline_queue
QUEUE_RETRY_INTERVAL_SECONDS=30
MAX_OFFLINE_QUEUE_FILES=300

DB_NAME=YOUR_DATABASE
DB_USER=YOUR_DATABASE_USER
DB_PASSWORD=YOUR_DATABASE_PASSWORD
DB_HOST=YOUR_DATABASE_HOST
DB_PORT=5432
DB_SSLMODE=require
DB_CONNECT_TIMEOUT_SECONDS=10
```

Never share the real `.env` publicly.

---

## 10. Bank and Branch Identification

The desktop client does not manually send a branch ID.

It sends:

```text
BANK_CODE
BANK_API_KEY
Windows PC Name
Image
```

The Windows hostname is read automatically.

Example:

```text
LAPTOP-D70CL59R
```

If a branch has:

```text
PC Prefix: LAPTOP
```

the machine matches that branch.

Production example:

```text
Branch: Ridge Towers
PC Prefix: FBLRDG

Computers:
FBLRDG001
FBLRDG002
FBLRDG003
```

Branch matching is scoped to the authenticated bank.

The longest matching prefix should win.

---

## 11. Generate or Rotate a Bank API Key

From:

```text
Smart-Customer-Sentiment-Analysis/emotion_dashboard
```

run:

```powershell
python manage.py set_bank_api_key FIDELITY_GH
```

Copy the generated raw key into the teller PC `.env`:

```env
BANK_API_KEY=THE_GENERATED_KEY
```

The database stores only a hash.

---

## 12. How to Run the Full Local System

Use three PowerShell windows.

### Terminal 1 - Django Dashboard

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
.venv\Scripts\Activate.ps1
cd emotion_dashboard
python manage.py runserver 8000
```

Open:

```text
http://127.0.0.1:8000/
```

### Terminal 2 - Face / Emotion API

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
.venv\Scripts\Activate.ps1
python -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

Health endpoint:

```text
http://127.0.0.1:8001/health
```

### Terminal 3 - Desktop Capture

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
.venv\Scripts\Activate.ps1
python desktop_capture.py
```

Press `Q` or `Esc` to stop preview mode.

---

## 13. How `desktop_capture.py` Works

```text
Read camera frame
    |
    v
Apply customer ROI
    |
    v
Detect faces
    |
    +-- No face -> wait
    |
    +-- Multiple faces -> reject frame
    |
    +-- Exactly one face
           |
           v
       Check minimum size
           |
           v
       Check blur
           |
           v
       Check brightness/exposure
           |
           v
       Check stability across frames
           |
           v
       Store good candidates
           |
           v
       Select best frame
           |
           v
       Upload in background
           |
           v
       Wait for customer to leave
           |
           v
       Reset for next customer
```

---

## 14. Region of Interest (ROI)

The system should not scan the entire banking hall unnecessarily.

The ROI defines the expected customer position.

```text
Full Camera Frame
+------------------------------------------------+
|                                                |
|        CUSTOMER CAPTURE REGION                 |
|          +--------------------+                |
|          |   Customer face    |                |
|          +--------------------+                |
|                                                |
+------------------------------------------------+
```

Configured using:

```env
ROI_LEFT=0.18
ROI_TOP=0.06
ROI_RIGHT=0.82
ROI_BOTTOM=0.96
```

During installation, calibrate this so that:

- the customer is included;
- the teller is excluded;
- the queue is excluded as much as possible;
- screens/documents are not unnecessarily captured.

---

## 15. Local Face Detection

The desktop client currently uses OpenCV for lightweight local face detection.

Local detection answers:

```text
Is there a usable customer face right now?
```

It is not the final identity or emotion model.

The heavier processing happens in FastAPI/DeepFace.

---

## 16. Exactly-One-Face Rule

The desktop workflow should continue only when exactly one acceptable customer face is visible inside the ROI.

This helps avoid accidentally processing:

- the teller;
- another customer;
- someone walking behind the customer;
- people waiting in a queue.

---

## 17. Minimum Face Size

Current starting configuration:

```env
MIN_FACE_WIDTH_PIXELS=120
MIN_FACE_HEIGHT_PIXELS=120
MIN_FACE_AREA_RATIO=0.035
```

These values must be calibrated using the actual teller camera, distance and resolution.

---

## 18. Blur Detection

Blur is estimated using Laplacian variance.

Conceptually:

```python
blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
```

Current threshold:

```env
BLUR_THRESHOLD=45
```

Test with:

```text
sharp stationary face
normal talking movement
head turning
walking into position
autofocus transition
low-light motion blur
```

Do not tune the threshold using only one person.

---

## 19. Brightness and Exposure

Current settings:

```env
MIN_BRIGHTNESS=45
MAX_BRIGHTNESS=215

MAX_DARK_PIXEL_PERCENT=0.58
MAX_BRIGHT_PIXEL_PERCENT=0.38
```

The goal is to reject:

- very dark faces;
- severe backlighting;
- severe overexposure;
- strong glare.

The customer should not need studio lighting.

---

## 20. Stable Face Detection

The system should not capture the first frame where a face appears.

The customer may be walking, turning, looking down or moving documents.

Current configuration:

```env
STABLE_FRAMES_REQUIRED=6
STABILITY_IOU_THRESHOLD=0.55
```

The system compares face position between frames before accepting candidate images.

---

## 21. Best-Frame Selection

Current configuration:

```env
SAMPLE_WINDOW_SECONDS=1.2
MIN_GOOD_CANDIDATES=4
```

Candidate frames are ranked using quality factors such as:

```text
sharpness
brightness
face size
basic eye visibility
```

The best frame is uploaded.

This is one of the main areas where the emotion-detection developer can improve the system.

---

## 22. Background Uploads

Network requests must not block:

```text
camera.read()
preview rendering
cv2.waitKey()
```

Uploads therefore run in background threads.

The preview should remain responsive even if:

- the API is slow;
- the database is temporarily unavailable;
- DeepFace takes time;
- the network is unstable.

---

## 23. API Request Format

The desktop client uploads to:

```text
POST /upload-face
```

Headers:

```text
X-Bank-Code
X-API-Key
```

Form field:

```text
pc_name
```

File:

```text
JPEG image
```

Conceptually:

```python
requests.post(
    FACE_API_URL,
    headers={
        "X-Bank-Code": BANK_CODE,
        "X-API-Key": BANK_API_KEY,
    },
    files={
        "file": (
            filename,
            image_bytes,
            "image/jpeg",
        )
    },
    data={
        "pc_name": PC_NAME
    },
    timeout=REQUEST_TIMEOUT_SECONDS,
)
```

---

## 24. HTTP Response Handling

Treat:

```text
2xx -> success
```

All `4xx` responses are terminal rejection for that specific request.

Examples:

```text
400 bad request
401 invalid API key
403 PC not assigned to branch
413 image too large
415 unsupported file
422 face/emotion processing rejection
```

Retryable situations include:

```text
connection errors
timeouts
500
503
```

Retryable captures can be saved to the offline queue.

---

## 25. Offline Queue

Retryable captures are stored in:

```text
offline_queue/
```

Configuration:

```env
QUEUE_RETRY_INTERVAL_SECONDS=30
MAX_OFFLINE_QUEUE_FILES=300
```

A background retry worker resends queued images.

Queue access must remain thread-safe because uploads and retry logic may run at the same time.

---

## 26. Duplicate Capture Prevention

After a successful capture, the system waits for the customer to leave.

State:

```text
Captured - waiting for customer to leave
```

It resets after no face is seen for:

```env
FACE_ABSENCE_RESET_SECONDS=1.8
```

Additional cooldown:

```env
CAPTURE_COOLDOWN_SECONDS=5
```

This prevents repeated captures of the same interaction.

---

## 27. What Happens in `face_api.py`

```text
Authenticate bank
    |
    v
Validate PC name
    |
    v
Determine branch from PC prefix
    |
    v
Decode image
    |
    v
Validate storage path
    |
    v
Save image
    |
    v
Extract face(s)
    |
    v
Generate embedding
    |
    v
Compare against SAME-BANK embeddings
    |
    +-- Match -> existing Face ID
    |
    +-- No match -> new Face ID
    |
    v
Run emotion analysis
    |
    v
Save visitor + snapshot
    |
    v
Commit after successful processing
```

A failed multi-face job should roll back its database changes rather than leaving partial records.

---

## 28. Face Embeddings

A face embedding is a numeric feature vector representing a face.

```text
Face image
    |
    v
Embedding model
    |
    v
[0.123, -0.482, 0.091, ...]
```

The configured model may be something such as:

```env
EMBEDDING_MODEL=ArcFace
```

Do not change embedding models casually.

Changing models may change vector dimensions and matching behaviour.

Before changing a model, define:

```text
new dimensionality
new threshold
migration strategy
whether old embeddings need regeneration
```

---

## 29. Face Matching

`api_server/face_utils.py` contains matching logic.

The new candidate embedding is compared with known embeddings from the **same bank only**.

Never perform global cross-bank matching.

Also skip vectors with incompatible dimensions.

---

## 30. Emotion Detection

The API uses DeepFace emotion analysis.

Conceptually:

```python
DeepFace.analyze(
    img_path=face_image,
    actions=["emotion"],
    enforce_detection=False,
)
```

The dashboard mainly uses:

```text
happy
neutral
sad
angry
surprise
```

Important:

The model estimates **visible facial expression**.

It should not be treated as perfect knowledge of what a customer internally feels.

Do not use emotion output alone to:

```text
accuse staff
judge truthfulness
approve/deny loans
deny banking service
make legal conclusions
```

The intended use is aggregate customer-service analytics.

---

## 31. Main Areas for the Emotion-Detection Developer

### A. Improve capture quality

Test:

```text
blur
dark lighting
overexposure
head turns
glasses
different customer heights
different skin tones
movement
multiple people
partial occlusion
```

### B. Build a camera calibration mode

Possible future screen:

```text
Face size: PASS
Brightness: PASS
Blur: PASS
Head pose: PASS
Customer ROI: PASS
Multiple faces: NO
Ready for deployment
```

### C. Evaluate a better lightweight face detector

The current local detector is intentionally lightweight.

Any replacement must be benchmarked for:

```text
accuracy
CPU
latency
false positives
false negatives
Windows compatibility
installation size
```

### D. Add head-pose quality checks

Reject or de-prioritize strongly turned faces.

### E. Investigate multi-frame emotion analysis

Possible experiment:

```text
Frame 1 -> neutral
Frame 2 -> neutral
Frame 3 -> happy

Aggregate -> neutral
```

Do not implement averaging blindly. Measure first.

### F. Evaluate real accuracy

Create a controlled validation dataset.

Record:

```text
expected visible expression
predicted expression
confidence
lighting
distance
head angle
blur
glasses
```

Use a confusion matrix.

---

## 32. Suggested Test Matrix

| Test | Expected |
|---|---|
| No person | No upload |
| One centered face | Capture |
| Face too far away | Reject |
| Very blurred face | Reject |
| Very dark face | Reject |
| Strong overexposure | Reject |
| Two faces in ROI | Reject |
| Teller outside ROI | Ignore teller |
| Customer moves then stops | Wait, then capture |
| Customer stays after capture | Do not repeatedly capture |
| Customer leaves | Reset |
| New customer arrives | New capture |
| API offline | Queue retryable capture |
| API returns 401 | Reject, do not endlessly retry |
| API returns 403 | Reject, check PC prefix |
| API restored | Retry offline queue |
| Same visitor returns later | Attempt same Face ID |
| Different bank | Never cross-match visitor |

---

## 33. Teller Camera Installation

Recommended:

```text
              CUSTOMER

                 |
                 v

       [ Customer-facing camera ]
                  O

        +-----------------------+
        |     Teller monitor    |
        +-----------------------+

                TELLER
```

Preferred camera characteristics:

```text
1080p
25-30 FPS
autofocus
reasonable low-light performance
wide dynamic range preferred
USB
```

Avoid an unnecessarily wide field of view.

---

## 34. Lighting Guidance

Avoid:

```text
bright window directly behind customer
harsh spotlight in customer's face
strong one-sided shadow
camera pointed toward entrance glare
```

Aim for visible:

```text
eyes
mouth
cheeks
forehead
```

without severe darkness or washout.

---

## 35. Preview Mode

During installation:

```env
PREVIEW_ENABLED=true
```

Use preview mode to tune:

```text
ROI
camera angle
face size
lighting
blur threshold
customer position
```

After calibration, production may use:

```env
PREVIEW_ENABLED=false
```

depending on operational requirements.

---

## 36. Debugging Workflow

### Camera not opening

Close:

```text
Windows Camera
Teams
Zoom
WhatsApp video
OBS
```

Try:

```env
CAMERA_INDEX=0
```

then possibly:

```env
CAMERA_INDEX=1
```

### API connection refused

Start FastAPI:

```powershell
python -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

Confirm:

```text
FACE_API_URL=http://127.0.0.1:8001/upload-face
```

### 401 Unauthorized

Check:

```text
BANK_CODE
BANK_API_KEY
```

A rotated API key invalidates the previous key.

### 403 Forbidden

Check hostname:

```powershell
hostname
```

or:

```powershell
python -c "import socket; print(socket.gethostname())"
```

Verify the bank has an active branch with a matching PC prefix.

### 422 Unprocessable Entity

Possible causes:

```text
no usable face
DeepFace processing failure
TensorFlow/TF-Keras compatibility
invalid image
```

Read the FastAPI terminal logs.

Do not automatically assume 422 means a branch problem.

### Preview freezes while uploading

Long network work has probably been moved back into the main camera loop.

Uploads and offline retries should stay in background workers.

---

## 37. Developer Workflow

Create a feature branch:

```powershell
git checkout -b feature/emotion-capture-improvements
```

Before changing detection logic:

1. Record current behaviour.
2. Make one logical change at a time.
3. Test it.
4. Measure whether it improved results.
5. Test multiple people and environments.
6. Do not commit customer images or `.env`.

Review changes:

```powershell
git status
git diff
```

Commit:

```powershell
git add desktop_capture.py api_server
git commit -m "Improve desktop face capture quality pipeline"
```

Push:

```powershell
git push -u origin feature/emotion-capture-improvements
```

---

## 38. Validation Before Commit

From project root:

```powershell
python -m py_compile desktop_capture.py
python -m py_compile api_server\config.py
python -m py_compile api_server\db_utils.py
python -m py_compile api_server\face_api.py
python -m py_compile api_server\face_utils.py
```

Then:

```powershell
cd emotion_dashboard

python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test monitor
```

Also manually test:

```text
Django login/dashboard
FastAPI health endpoint
camera preview
successful capture
branch assignment
emotion result
offline API behaviour
queue recovery
```

---

## 39. Useful Development Logging

For capture experiments, log:

```text
timestamp
PC name
number of detected faces
face size
face area ratio
blur score
brightness
dark-pixel percentage
bright-pixel percentage
stability count
quality score
accepted/rejected
rejection reason
API result
processing time
```

Never log:

```text
raw API keys
database passwords
unnecessary customer personal information
```

---

## 40. Performance Requirements

The teller PC must remain usable.

Monitor:

```text
CPU
RAM
camera FPS
preview responsiveness
upload latency
DeepFace processing time
offline queue growth
```

Heavy ML work should generally remain on the API/processing side unless the architecture is intentionally redesigned.

---

## 41. Privacy and Multi-Tenant Security

This system processes face images and embeddings.

Rules:

- capture only what is needed;
- keep `captured_faces/` outside public static serving;
- authorize every image request;
- keep API keys secret;
- isolate banks and branches;
- never compare Bank A embeddings with Bank B;
- apply retention policies;
- avoid unnecessary image duplication;
- use authorized test data.

Correct tenant flow:

```text
Bank A API key
    ->
Bank A branches only
    ->
Bank A visitors only
    ->
Bank A embeddings only
```

---

## 42. Transaction Integrity

A processing job should be atomic.

Correct:

```text
Face 1 prepared
Face 2 prepared
Face 3 fails
        |
        v
ROLLBACK ALL JOB DATABASE WRITES
```

Do not commit inside each individual snapshot save.

Commit only after the overall processing operation succeeds.

---

## 43. Image / Database Consistency

Avoid:

```text
database row exists but image is missing
```

and:

```text
image exists after processing failed
```

Be careful when modifying:

```text
process_face_image()
upload_face()
save_snapshot_to_db()
```

---

## 44. Good First Tasks for the New Developer

### Task 1
Build a capture-quality benchmark tool.

### Task 2
Measure current thresholds across several participants and lighting conditions.

### Task 3
Test a better local detector against the current detector.

### Task 4
Add head-pose scoring.

### Task 5
Experiment with multi-frame emotion stability.

### Task 6
Measure DeepFace emotion confusion matrix.

### Task 7
Document camera calibration values for a real teller desk.

---

## 45. Pull Request Checklist

Every PR should state:

```text
What changed?
Why?
Which files changed?
What was the old behaviour?
What is the new behaviour?
How was it tested?
Which cameras?
Which lighting conditions?
Any dependency changes?
Any .env changes?
Any database changes?
Known limitations?
```

For detection changes, include measurements.

Example:

```text
Before:
67/100 usable faces accepted
18 blurred frames incorrectly accepted

After:
84/100 usable faces accepted
5 blurred frames incorrectly accepted

Test:
5 participants
2 lighting conditions
2 distances
```

---

## 46. Quick Start Checklist

```text
[ ] Clone/download latest project
[ ] Create/activate .venv
[ ] Install requirements
[ ] Verify OpenCV
[ ] Verify TensorFlow + TF-Keras
[ ] Verify DeepFace
[ ] Create local .env
[ ] Configure PostgreSQL
[ ] Configure BANK_CODE
[ ] Configure BANK_API_KEY
[ ] Configure a matching branch PC prefix
[ ] Run Django on 8000
[ ] Run FastAPI on 8001
[ ] Run desktop_capture.py
[ ] Stand inside ROI
[ ] Verify quality checks
[ ] Verify one capture uploads
[ ] Verify correct branch
[ ] Verify emotion appears in dashboard
[ ] Verify customer must leave before reset
[ ] Stop API and test offline queue
[ ] Restart API and verify queue recovery
```

---

## 47. Most-Used Commands

### Dashboard

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
.venv\Scripts\Activate.ps1
cd emotion_dashboard
python manage.py runserver 8000
```

### Face API

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
.venv\Scripts\Activate.ps1
python -m uvicorn api_server.face_api:app --host 127.0.0.1 --port 8001
```

### Desktop Capture

```powershell
cd C:\Users\YOUR_NAME\path\to\Smart-Customer-Sentiment-Analysis
.venv\Scripts\Activate.ps1
python desktop_capture.py
```

---

## 48. Final Architecture Summary

```text
                    BANK CUSTOMER
                         |
                         v
                 Teller Camera
                         |
                         v
                desktop_capture.py
                         |
        +----------------+----------------+
        |                                 |
        v                                 v
Local quality gate                 Offline Queue
ROI / one face / blur              for retryable
light / size / stability             failures
best frame                              |
        |                               |
        +---------------+---------------+
                        |
                        v
             POST /upload-face
                        |
                        v
               FastAPI Face API
                        |
          +-------------+-------------+
          |                           |
          v                           v
 Bank authentication          PC -> Branch mapping
          |                           |
          +-------------+-------------+
                        |
                        v
                DeepFace pipeline
                        |
          +-------------+-------------+
          |                           |
          v                           v
   Face embedding               Emotion analysis
          |                           |
          v                           |
 SAME-BANK face matching              |
          |                           |
          +-------------+-------------+
                        |
                        v
                  PostgreSQL
                        |
                        v
                 Django Dashboard
```

The desktop capture component's main responsibility is:

> **Consistently select the best possible customer face, at the correct time, without disrupting the teller workstation, and securely deliver that image to the processing API.**

The API's responsibility is:

> **Authenticate the source, determine the correct bank and branch, perform face and emotion processing, preserve transaction integrity, and securely persist the result.**

The dashboard's responsibility is:

> **Present authorized sentiment and visitor analytics to the appropriate bank, branch and platform users.**
