import json
from datetime import datetime

import numpy as np
import psycopg2

from .config import DB_CONFIG

def _normalize_db_config(cfg):
    # Accept either a Django-style wrapper (with "default") or a flat mapping.
    if isinstance(cfg, dict) and "default" in cfg:
        cfg = cfg["default"]
    if not isinstance(cfg, dict):
        raise ValueError("DB_CONFIG must be a dict or include a 'default' dict")

    # Map common Django-style keys to psycopg2 parameters.
    dbname = cfg.get("NAME")
    user = cfg.get("USER")
    password = cfg.get("PASSWORD")
    host = cfg.get("HOST")
    port = cfg.get("PORT")
    sslmode = None
    options = cfg.get("OPTIONS") or {}
    if isinstance(options, dict):
        sslmode = options.get("sslmode")

    return {
        "dbname": dbname,
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "sslmode": sslmode or "require",
    }

def get_db():
    cfg = _normalize_db_config(DB_CONFIG)
    return psycopg2.connect(**cfg)

def ensure_tables_exist(db):
    cur = db.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS captured_snapshots (
            id SERIAL PRIMARY KEY,
            face_id VARCHAR(128) NOT NULL,
            pc_name VARCHAR(128),
            image_path TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            embedding TEXT
        );
        """
    )
    db.commit()
    cur.close()

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
