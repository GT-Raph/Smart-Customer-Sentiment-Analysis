"""Small PostgreSQL data-access layer shared by the API and worker."""

from __future__ import annotations

import secrets
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

import numpy as np
import psycopg2
from psycopg2.extras import Json, RealDictCursor

from .config import settings
from .security import api_key_prefix, hash_api_key


@dataclass(frozen=True)
class DeviceContext:
    id: int
    organization_id: int
    branch_id: int
    name: str
    pc_name: str
    plan: str = "free"
    monthly_analysis_limit: int = 1000


class QuotaExceeded(RuntimeError):
    pass


@contextmanager
def database() -> Iterator[Any]:
    """Open a short-lived database connection and always close it."""
    connection = psycopg2.connect(settings.database_url, connect_timeout=10)
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

    with database() as db, db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT d.id, d.organization_id, d.branch_id, d.name, d.pc_name,
                   d.api_key_hash, o.plan, o.monthly_analysis_limit
              FROM monitor_device d
              JOIN monitor_organization o ON o.id = d.organization_id
              JOIN monitor_branch b ON b.id = d.branch_id
             WHERE d.api_key_prefix = %s
               AND d.is_active = TRUE
               AND o.is_active = TRUE
               AND o.subscription_status IN ('trialing', 'active')
               AND b.is_active = TRUE
               AND b.organization_id = d.organization_id
             LIMIT 1
            """,
            (prefix,),
        )
        row = cursor.fetchone()
        if not row or not secrets.compare_digest(row["api_key_hash"], hash_api_key(token)):
            return None

        cursor.execute(
            "UPDATE monitor_device SET last_seen_at = %s WHERE id = %s",
            (datetime.now(timezone.utc), row["id"]),
        )
        return DeviceContext(
            id=row["id"],
            organization_id=row["organization_id"],
            branch_id=row["branch_id"],
            name=row["name"],
            pc_name=row["pc_name"] or row["name"],
            plan=row["plan"],
            monthly_analysis_limit=row["monthly_analysis_limit"],
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
        now = datetime.now(timezone.utc)
        period_start = now.date().replace(day=1)
        if device.monthly_analysis_limit > 0:
            cursor.execute(
                """
                INSERT INTO monitor_monthlyusage (
                    organization_id, period_start, analyses_count, updated_at
                ) VALUES (%s, %s, 1, %s)
                ON CONFLICT (organization_id, period_start)
                DO UPDATE SET analyses_count = monitor_monthlyusage.analyses_count + 1,
                              updated_at = EXCLUDED.updated_at
                WHERE monitor_monthlyusage.analyses_count < %s
                RETURNING analyses_count
                """,
                (device.organization_id, period_start, now, device.monthly_analysis_limit),
            )
            if cursor.fetchone() is None:
                raise QuotaExceeded("Monthly analysis quota exceeded")
        else:
            cursor.execute(
                """
                INSERT INTO monitor_monthlyusage (
                    organization_id, period_start, analyses_count, updated_at
                ) VALUES (%s, %s, 1, %s)
                ON CONFLICT (organization_id, period_start)
                DO UPDATE SET analyses_count = monitor_monthlyusage.analyses_count + 1,
                              updated_at = EXCLUDED.updated_at
                """,
                (device.organization_id, period_start, now),
            )

        cursor.execute(
            """
            INSERT INTO captured_snapshots (
                job_id, organization_id, branch_id, device_id, pc_name, session_id,
                image_path, upload_content_type, upload_size_bytes,
                status, processed, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued', FALSE, %s)
            RETURNING id
            """,
            (
                job_id,
                device.organization_id,
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
        return int(cursor.fetchone()[0])


def get_snapshot(snapshot_id: int) -> dict[str, Any] | None:
    with database() as db, db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "SELECT * FROM captured_snapshots WHERE id = %s",
            (snapshot_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_snapshot_for_device(job_id: str, device: DeviceContext) -> dict[str, Any] | None:
    with database() as db, db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, job_id, status, emotion, confidence, error_message,
                   image_path, timestamp, processed_at
              FROM captured_snapshots
             WHERE job_id = %s
               AND organization_id = %s
               AND device_id = %s
             LIMIT 1
            """,
            (job_id, device.organization_id, device.id),
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
               SET status = 'failed', processed = FALSE,
                   error_message = %s, processed_at = %s
             WHERE id = %s
            """,
            (safe_message, datetime.now(timezone.utc), snapshot_id),
        )


def get_embeddings(organization_id: int) -> list[tuple[int, str, np.ndarray]]:
    with database() as db, db.cursor() as cursor:
        cursor.execute(
            """
            SELECT v.id, v.face_id, s.embedding
              FROM monitor_visitor v
              JOIN LATERAL (
                    SELECT embedding
                      FROM captured_snapshots cs
                     WHERE cs.visitor_id = v.id
                       AND cs.embedding IS NOT NULL
                     ORDER BY cs.timestamp DESC
                     LIMIT 1
              ) s ON TRUE
             WHERE v.organization_id = %s
            """,
            (organization_id,),
        )
        known: list[tuple[int, str, np.ndarray]] = []
        for visitor_id, face_id, value in cursor.fetchall():
            try:
                embedding = value
                if isinstance(value, str):
                    embedding = json.loads(value)
                known.append(
                    (visitor_id, face_id, np.asarray(embedding, dtype=np.float64))
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return known


def create_visitor(organization_id: int, face_id: str) -> int:
    now = datetime.now(timezone.utc)
    with database() as db, db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO monitor_visitor (organization_id, face_id, first_seen, last_seen)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (organization_id, face_id)
            DO UPDATE SET last_seen = EXCLUDED.last_seen
            RETURNING id
            """,
            (organization_id, face_id, now, now),
        )
        return int(cursor.fetchone()[0])


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
        completed_at = datetime.now(timezone.utc)
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
                   processed = TRUE,
                   error_message = '',
                   processed_at = %s
             WHERE id = %s
            """,
            (
                visitor_id,
                emotion,
                confidence,
                Json(emotion_vector),
                Json(embedding) if embedding is not None else None,
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
