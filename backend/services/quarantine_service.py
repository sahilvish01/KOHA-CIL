"""
KOHA-CIL — Quarantine Service
CRUD operations for quarantine_records (conflict management).
"""
from __future__ import annotations

import logging
from typing import List, Optional

from database.connection import get_db
from models.schemas import QuarantineRecord, ConflictStatus

logger = logging.getLogger(__name__)


def create_quarantine_record(
    source_document: str,
    field_name: str,
    existing_value: str,
    incoming_value: str,
    reason: str,
    subsidiary: Optional[str] = None,
    financial_year: Optional[str] = None,
    mine_type: Optional[str] = None,
) -> int:
    """Insert a new quarantine record. Returns the new record ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO quarantine_records
                (source_document, field_name, existing_value, incoming_value,
                 reason, subsidiary, financial_year, mine_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_document, field_name, existing_value, incoming_value,
             reason, subsidiary, financial_year, mine_type),
        )
        return cursor.lastrowid


def get_all_quarantine(status: Optional[str] = None) -> List[dict]:
    """Retrieve quarantine records, optionally filtered by status."""
    if status:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM quarantine_records WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
    else:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM quarantine_records ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_quarantine_by_id(record_id: int) -> Optional[dict]:
    """Retrieve a single quarantine record by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM quarantine_records WHERE id = ?", (record_id,)
        ).fetchone()
    return dict(row) if row else None


def review_quarantine(record_id: int, action: str, reviewer: str) -> bool:
    """
    Approve or reject a quarantine record.
    
    action must be 'APPROVED' or 'REJECTED'.
    Returns True if the record was found and updated.
    """
    valid_actions = {"APPROVED", "REJECTED"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}")

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE quarantine_records
            SET status = ?, reviewed_by = ?, reviewed_at = datetime('now')
            WHERE id = ? AND status = 'PENDING_REVIEW'
            """,
            (action, reviewer, record_id),
        )
        return cursor.rowcount > 0


def count_pending() -> int:
    """Return count of PENDING_REVIEW quarantine records."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM quarantine_records WHERE status = 'PENDING_REVIEW'"
        ).fetchone()
    return row["cnt"] if row else 0
