import sys
import os

# allow importing from parent folder
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from face_api import app


@app.get("/")
def root():
    return {"status": "API running"}


@app.get("/test")
def test():
    return {"message": "working"}
