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
    """Review a quarantined value and atomically apply approved production changes.

    Rejections only resolve the quarantine item.  An approval updates the matching
    trusted production record before marking the quarantine item approved, so a
    failed/invalid synchronization cannot leave an approved but unapplied review.
    """
    valid_actions = {"APPROVED", "REJECTED"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}")

    with get_db() as conn:
        record = conn.execute(
            "SELECT * FROM quarantine_records WHERE id = ? AND status = 'PENDING_REVIEW'",
            (record_id,),
        ).fetchone()
        if record is None:
            return False

        if action == "APPROVED":
            if record["field_name"] != "production_mt":
                raise ValueError(f"Unsupported approved field '{record['field_name']}'.")
            if not all(record[key] for key in ("subsidiary", "financial_year", "mine_type")):
                raise ValueError("Approved production conflict is missing its record identity.")
            try:
                incoming_production = float(record["incoming_value"])
            except (TypeError, ValueError) as exc:
                raise ValueError("Approved incoming production value must be numeric.") from exc

            cursor = conn.execute(
                """
                UPDATE production_statistics
                SET production_mt = ?,
                    achievement_percentage = CASE
                        WHEN target_mt > 0 THEN ROUND(? / target_mt * 100, 2)
                        ELSE 0
                    END
                WHERE subsidiary = ? AND financial_year = ? AND mine_type = ?
                """,
                (incoming_production, incoming_production, record["subsidiary"],
                 record["financial_year"], record["mine_type"]),
            )
            if cursor.rowcount != 1:
                raise ValueError("No trusted production record matched the approved conflict.")

        conn.execute(
            """
            UPDATE quarantine_records
            SET status = ?, reviewed_by = ?, reviewed_at = datetime('now')
            WHERE id = ? AND status = 'PENDING_REVIEW'
            """,
            (action, reviewer, record_id),
        )
        return True


def count_pending() -> int:
    """Return count of PENDING_REVIEW quarantine records."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM quarantine_records WHERE status = 'PENDING_REVIEW'"
        ).fetchone()
    return row["cnt"] if row else 0
