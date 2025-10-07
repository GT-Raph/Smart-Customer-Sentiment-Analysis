import mysql.connector
import json
import numpy as np
from datetime import datetime
from .config import DB_CONFIG

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def get_embeddings_db(cursor):
    cursor.execute("SELECT face_id, embedding FROM captured_snapshots WHERE embedding IS NOT NULL")
    known = []
    for face_id, emb_json in cursor.fetchall():
        try:
            emb = np.array(json.loads(emb_json), dtype=np.float64)
            known.append((face_id, emb))
        except Exception:
            continue
    return known

def save_snapshot_to_db(db, face_id, pc_name, image_path, timestamp, embedding):
    cursor = db.cursor()
    sql = """
        INSERT INTO captured_snapshots (face_id, pc_name, image_path, timestamp, embedding)
        VALUES (%s, %s, %s, %s, %s)
    """
    emb_json = json.dumps(embedding.tolist()) if embedding is not None else None
    if isinstance(timestamp, str):
        timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    cursor.execute(sql, (face_id, pc_name, image_path, timestamp, emb_json))
    db.commit()
    cursor.close()
