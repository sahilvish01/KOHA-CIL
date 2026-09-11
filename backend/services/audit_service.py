"""
KOHA-CIL — Audit Service
Records all significant operations to the audit_log table.
"""
from __future__ import annotations

import logging
from typing import Optional

from database.connection import get_db

logger = logging.getLogger(__name__)


def log_event(
    request_id: str,
    username: str,
    role: str,
    subsidiary: Optional[str],
    action: str,
    query: Optional[str] = None,
    intent: Optional[str] = None,
    result_summary: Optional[str] = None,
    citation_count: int = 0,
    conflict_status: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Insert an audit record. Failures are logged but never propagate to the caller.
    """
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                    (request_id, username, role, subsidiary, action, query,
                     intent, result_summary, citation_count, conflict_status, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    username,
                    role,
                    subsidiary,
                    action,
                    query,
                    intent,
                    result_summary,
                    citation_count,
                    conflict_status,
                    ip_address,
                ),
            )
    except Exception as exc:
        logger.error("Audit log write failed: %s", exc)


def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    username: Optional[str] = None,
    action: Optional[str] = None,
) -> list:
    """Retrieve audit log records with optional filtering."""
    conditions = []
    params: list = []

    if username:
        conditions.append("username = ?")
        params.append(username)
    if action:
        conditions.append("action = ?")
        params.append(action)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM audit_log
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()

    return [dict(r) for r in rows]
