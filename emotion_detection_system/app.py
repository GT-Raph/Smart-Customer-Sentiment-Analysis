from flask import Flask, render_template, jsonify, send_from_directory
import mysql.connector
import os

app = Flask(__name__)
CAPTURED_FOLDER = "captured_faces"

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="emotion_detection"
)
cursor = db.cursor(dictionary=True)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/faces")
def get_faces():
    cursor.execute("SELECT * FROM recognition_logs ORDER BY timestamp DESC LIMIT 50")
    logs = cursor.fetchall()
    return jsonify(logs)

@app.route("/captured_faces/<filename>")
def get_face_image(filename):
    return send_from_directory(CAPTURED_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)
