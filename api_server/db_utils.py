"""Small MySQL/MariaDB data-access layer shared by the API and worker."""

from __future__ import annotations

import json
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

import numpy as np
import MySQLdb
from MySQLdb.cursors import DictCursor

from .config import settings
from .security import api_key_prefix, hash_api_key


@dataclass(frozen=True)
class DeviceContext:
    id: int
    branch_id: int
    name: str
    pc_name: str


def utc_now_for_database() -> datetime:
    """Return naive UTC because MySQL/MariaDB DATETIME has no timezone offset."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


@contextmanager
def database() -> Iterator[Any]:
    """Open a short-lived database connection and always close it."""
    connection = MySQLdb.connect(**settings.mysql_options)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def authenticate_device(token: str) -> DeviceContext | None:
    prefix = api_key_prefix(token)
    if not prefix:
        return None

    with database() as db, db.cursor(DictCursor) as cursor:
        cursor.execute(
            """
            SELECT d.id, d.branch_id, d.name, d.pc_name, d.api_key_hash
              FROM monitor_device d
              JOIN monitor_branch b ON b.id = d.branch_id
             WHERE d.api_key_prefix = %s
               AND d.is_active = 1
               AND b.is_active = 1
             LIMIT 1
            """,
            (prefix,),
        )
        row = cursor.fetchone()
        if not row or not secrets.compare_digest(row["api_key_hash"], hash_api_key(token)):
            return None

        cursor.execute(
            "UPDATE monitor_device SET last_seen_at = %s WHERE id = %s",
            (utc_now_for_database(), row["id"]),
        )
        return DeviceContext(
            id=row["id"],
            branch_id=row["branch_id"],
            name=row["name"],
            pc_name=row["pc_name"] or row["name"],
        )


def insert_snapshot(
    *,
    job_id: str,
    device: DeviceContext,
    image_path: str,
    content_type: str,
    size_bytes: int,
    session_id: str,
) -> int:
    with database() as db, db.cursor() as cursor:
        now = utc_now_for_database()
        cursor.execute(
            """
            INSERT INTO captured_snapshots (
                job_id, branch_id, device_id, pc_name, session_id,
                image_path, upload_content_type, upload_size_bytes,
                status, processed, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'queued', 0, %s)
            """,
            (
                job_id,
                device.branch_id,
                device.id,
                device.pc_name,
                session_id,
                image_path,
                content_type,
                size_bytes,
                now,
            ),
        )
        return int(cursor.lastrowid)


def get_snapshot(snapshot_id: int) -> dict[str, Any] | None:
    with database() as db, db.cursor(DictCursor) as cursor:
        cursor.execute(
            "SELECT * FROM captured_snapshots WHERE id = %s",
            (snapshot_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_snapshot_for_device(job_id: str, device: DeviceContext) -> dict[str, Any] | None:
    with database() as db, db.cursor(DictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, job_id, status, emotion, confidence, error_message,
                   image_path, timestamp, processed_at
             FROM captured_snapshots
             WHERE job_id = %s
               AND device_id = %s
             LIMIT 1
            """,
            (job_id, device.id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def mark_processing(snapshot_id: int) -> None:
    with database() as db, db.cursor() as cursor:
        cursor.execute(
            """
            UPDATE captured_snapshots
               SET status = 'processing', error_message = ''
             WHERE id = %s
            """,
            (snapshot_id,),
        )


def mark_failed(snapshot_id: int, error_message: str) -> None:
    safe_message = error_message[:500]
    with database() as db, db.cursor() as cursor:
        cursor.execute(
            """
            UPDATE captured_snapshots
               SET status = 'failed', processed = 0,
                   error_message = %s, processed_at = %s
             WHERE id = %s
            """,
            (safe_message, utc_now_for_database(), snapshot_id),
        )


def get_embeddings() -> list[tuple[int, str, np.ndarray]]:
    with database() as db, db.cursor() as cursor:
        cursor.execute(
            """
            SELECT v.id, v.face_id, s.embedding
              FROM monitor_visitor v
              JOIN captured_snapshots s
                ON s.id = (
                    SELECT latest.id
                      FROM captured_snapshots latest
                     WHERE latest.visitor_id = v.id
                       AND latest.embedding IS NOT NULL
                     ORDER BY latest.timestamp DESC, latest.id DESC
                     LIMIT 1
                )
            """
        )
        known: list[tuple[int, str, np.ndarray]] = []
        for visitor_id, face_id, value in cursor.fetchall():
            try:
                embedding = value
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                if isinstance(value, str):
                    embedding = json.loads(value)
                known.append(
                    (visitor_id, face_id, np.asarray(embedding, dtype=np.float64))
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return known


def create_visitor(face_id: str) -> int:
    now = utc_now_for_database()
    with database() as db, db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO monitor_visitor (face_id, first_seen, last_seen)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id = LAST_INSERT_ID(id),
                last_seen = VALUES(last_seen)
            """,
            (face_id, now, now),
        )
        return int(cursor.lastrowid)


def complete_snapshot(
    *,
    snapshot_id: int,
    visitor_id: int,
    emotion: str,
    confidence: float,
    emotion_vector: dict[str, float],
    embedding: list[float] | None,
    image_path: str | None,
) -> None:
    with database() as db, db.cursor() as cursor:
        completed_at = utc_now_for_database()
        cursor.execute(
            "UPDATE monitor_visitor SET last_seen = %s WHERE id = %s",
            (completed_at, visitor_id),
        )
        cursor.execute(
            """
            UPDATE captured_snapshots
               SET visitor_id = %s,
                   emotion = %s,
                   confidence = %s,
                   emotion_vector = %s,
                   embedding = %s,
                   image_path = %s,
                   status = 'processed',
                   processed = 1,
                   error_message = '',
                   processed_at = %s
             WHERE id = %s
            """,
            (
                visitor_id,
                emotion,
                confidence,
                json.dumps(emotion_vector),
                json.dumps(embedding) if embedding is not None else None,
                image_path,
                completed_at,
                snapshot_id,
            ),
        )


def database_is_ready() -> bool:
    try:
        with database() as db, db.cursor() as cursor:
            cursor.execute("SELECT 1 FROM captured_snapshots LIMIT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False
