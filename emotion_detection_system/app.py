from flask import Flask, render_template, jsonify, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CAPTURED_FOLDER = "captured_faces"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres.uqkodzbevzooiqdxnfjq",
        "PASSWORD": "Z9/Fu*nC$mNTs/+",
        "HOST": "aws-1-eu-central-1.pooler.supabase.com",
        "PORT": "6543",
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}


def get_db_connection():
    cfg = DATABASES["default"]
    return psycopg2.connect(
        dbname=cfg["NAME"],
        user=cfg["USER"],
        password=cfg["PASSWORD"],
        host=cfg["HOST"],
        port=cfg["PORT"],
        sslmode=cfg["OPTIONS"].get("sslmode", "require"),
    )

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/faces")
def get_faces():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM recognition_logs ORDER BY timestamp DESC LIMIT 50")
    logs = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(logs)

@app.route("/captured_faces/<filename>")
def get_face_image(filename):
    return send_from_directory(CAPTURED_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)
