import hashlib
import hmac
import json
from datetime import datetime, timezone

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from .config import DB_CONFIG


def get_db():
    """
    Create a new PostgreSQL database connection.
    """
    missing_settings = [
        key
        for key, value in DB_CONFIG.items()
        if key != "sslmode" and not value
    ]

    if missing_settings:
        raise RuntimeError(
            "Missing database settings: "
            + ", ".join(missing_settings)
        )

    return psycopg2.connect(
        **DB_CONFIG
    )


def verify_bank_api_key(
    cursor,
    bank_code,
    raw_api_key,
):
    """
    Verify that the supplied API key belongs to the bank.

    API keys are stored only as SHA-256 hashes.
    """
    normalized_bank_code = (
        bank_code.strip().upper()
    )

    cursor.execute(
        """
        SELECT
            id,
            code,
            name,
            api_key_hash
        FROM tenant_bank
        WHERE code = %s
          AND is_active = TRUE
        """,
        (
            normalized_bank_code,
        ),
    )

    bank = cursor.fetchone()

    if not bank:
        return None

    if not raw_api_key:
        return None

    supplied_hash = hashlib.sha256(
        raw_api_key.encode("utf-8")
    ).hexdigest()

    stored_hash = (
        bank["api_key_hash"]
        or ""
    )

    api_key_is_valid = hmac.compare_digest(
        stored_hash,
        supplied_hash,
    )

    if not api_key_is_valid:
        return None

    return bank


def get_branch_by_pc_name(
    cursor,
    bank_id,
    pc_name,
):
    """
    Find the branch belonging to this bank whose configured
    PC prefix matches the beginning of the computer name.

    Examples:

        PC name: FBLRGE001
        Prefix:  FBLRGE
        Branch:  Ridge Towers

        PC name: FBLNUN004
        Prefix:  FBLNUN
        Branch:  Nungua

    Prefix matching is bank-specific. Another bank can use
    an entirely different naming system.

    When more than one prefix matches, the longest prefix wins.
    This avoids a short prefix taking priority over a more
    specific prefix.
    """
    normalized_pc_name = (
        pc_name.strip().upper()
    )

    if not normalized_pc_name:
        return None

    cursor.execute(
        """
        SELECT
            id,
            bank_id,
            code,
            name,
            pc_prefix,
            location
        FROM tenant_branch
        WHERE bank_id = %s
          AND is_active = TRUE
          AND pc_prefix IS NOT NULL
          AND BTRIM(pc_prefix) <> ''
        """,
        (
            bank_id,
        ),
    )

    matching_branches = []

    for branch_row in cursor.fetchall():
        branch = dict(
            branch_row
        )

        configured_prefix = (
            branch["pc_prefix"]
            or ""
        ).strip()

        normalized_prefix = (
            configured_prefix.upper()
        )

        if not normalized_prefix:
            continue

        if normalized_pc_name.startswith(
            normalized_prefix
        ):
            branch["matched_prefix"] = (
                configured_prefix
            )

            matching_branches.append(
                branch
            )

    if not matching_branches:
        return None

    matching_branches.sort(
        key=lambda branch: len(
            (
                branch["pc_prefix"]
                or ""
            ).strip()
        ),
        reverse=True,
    )

    return matching_branches[0]


def get_embeddings_db(
    cursor,
    bank_id,
):
    """
    Return known face embeddings belonging only to one bank.

    A face from one bank is never compared with a face
    belonging to another bank.
    """
    cursor.execute(
        """
        SELECT
            visitor.face_id,
            snapshot.embedding
        FROM analytics_snapshot AS snapshot

        INNER JOIN analytics_visitor AS visitor
            ON visitor.id = snapshot.visitor_id

        WHERE snapshot.bank_id = %s
          AND snapshot.embedding IS NOT NULL
          AND snapshot.status = 'done'

        ORDER BY snapshot.timestamp DESC
        """,
        (
            bank_id,
        ),
    )

    known_embeddings = []

    for database_row in cursor.fetchall():
        try:
            embedding_value = (
                database_row["embedding"]
            )

            if isinstance(
                embedding_value,
                str,
            ):
                embedding_value = json.loads(
                    embedding_value
                )

            embedding_array = np.asarray(
                embedding_value,
                dtype=np.float64,
            )

            known_embeddings.append(
                (
                    database_row["face_id"],
                    embedding_array,
                )
            )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            continue

    return known_embeddings


def save_snapshot_to_db(
    database,
    *,
    job_id,
    bank_id,
    branch_id,
    face_id,
    pc_name,
    image_path,
    embedding,
    emotion,
    confidence,
    emotion_vector,
):
    """
    Save a visitor and sentiment snapshot.

    Every visitor and snapshot is explicitly linked to a bank.
    """
    current_time = datetime.now(
        timezone.utc
    )

    clean_embedding = [
        float(value)
        for value in embedding
    ]

    clean_emotion_vector = {
        str(emotion_name): float(emotion_value)
        for emotion_name, emotion_value
        in emotion_vector.items()
    }

    embedding_json = json.dumps(
        clean_embedding
    )

    emotion_vector_json = json.dumps(
        clean_emotion_vector
    )

    normalized_pc_name = (
        pc_name.strip().upper()
    )

    with database.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:
        cursor.execute(
            """
            INSERT INTO analytics_visitor (
                bank_id,
                face_id,
                first_seen,
                last_seen
            )
            VALUES (
                %s,
                %s,
                %s,
                %s
            )

            ON CONFLICT (
                bank_id,
                face_id
            )
            DO UPDATE SET
                last_seen = EXCLUDED.last_seen

            RETURNING id
            """,
            (
                bank_id,
                face_id,
                current_time,
                current_time,
            ),
        )

        visitor_id = cursor.fetchone()[
            "id"
        ]

        cursor.execute(
            """
            INSERT INTO analytics_snapshot (
                job_id,
                bank_id,
                branch_id,
                visitor_id,
                pc_name,
                image_path,
                timestamp,
                emotion,
                confidence,
                emotion_vector,
                embedding,
                processed,
                status,
                processing_error
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::jsonb,
                %s::jsonb,
                TRUE,
                'done',
                ''
            )
            """,
            (
                job_id,
                bank_id,
                branch_id,
                visitor_id,
                normalized_pc_name,
                image_path,
                current_time,
                emotion,
                confidence,
                emotion_vector_json,
                embedding_json,
            ),
        )

    database.commit()


def db_healthcheck():
    """
    Confirm that the PostgreSQL connection is working.
    """
    with get_db() as database:
        with database.cursor() as cursor:
            cursor.execute(
                "SELECT 1"
            )

            result = cursor.fetchone()

    return bool(
        result
        and result[0] == 1
    )