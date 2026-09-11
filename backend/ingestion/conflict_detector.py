"""
KOHA-CIL — Conflict Detector
Compares incoming production statistics against existing trusted values.
Never silently overwrites trusted information.
Conflicting records are sent to quarantine.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from database.connection import get_db
from services.quarantine_service import create_quarantine_record

logger = logging.getLogger(__name__)

# Tolerance for floating-point comparison (within 0.01 MT = no conflict)
FLOAT_TOLERANCE = 0.01


def _values_conflict(existing: float, incoming: float) -> bool:
    """Return True if values differ beyond the defined tolerance."""
    return abs(existing - incoming) > FLOAT_TOLERANCE


def check_and_quarantine(stat_records: List[dict]) -> Tuple[List[dict], List[int]]:
    """
    For each incoming statistical record:
    - If no existing record: safe to insert.
    - If existing record matches: skip (idempotent).
    - If existing record conflicts: quarantine the incoming record, preserve existing.

    Returns:
        (safe_records, quarantine_ids)
        safe_records: records that can be safely inserted/ignored
        quarantine_ids: IDs of newly created quarantine records
    """
    safe_records: List[dict] = []
    quarantine_ids: List[int] = []

    for record in stat_records:
        subsidiary = record.get("subsidiary")
        financial_year = record.get("financial_year")
        mine_type = record.get("mine_type", "TOTAL")
        incoming_production = record.get("production_mt")

        if not (subsidiary and financial_year and incoming_production is not None):
            safe_records.append(record)
            continue

        # Look up existing trusted value
        with get_db() as conn:
            existing = conn.execute(
                """
                SELECT production_mt, source_document
                FROM production_statistics
                WHERE subsidiary = ? AND financial_year = ? AND mine_type = ?
                """,
                (subsidiary, financial_year, mine_type),
            ).fetchone()

        if existing is None:
            # No existing record — safe to insert
            safe_records.append(record)
            continue

        existing_production = existing["production_mt"]

        if not _values_conflict(existing_production, incoming_production):
            # Values match — skip (idempotent, no duplicate)
            logger.debug(
                "No conflict for %s %s %s — values match (%.2f MT)",
                subsidiary, financial_year, mine_type, existing_production,
            )
            continue

        # Values conflict — quarantine the incoming record
        reason = (
            f"Incoming production_mt ({incoming_production:.2f} MT) "
            f"differs from existing trusted value ({existing_production:.2f} MT) "
            f"for {subsidiary} {financial_year} {mine_type}."
        )
        logger.warning("CONFLICT DETECTED: %s", reason)

        qid = create_quarantine_record(
            source_document=record.get("source_document", "UNKNOWN"),
            field_name="production_mt",
            existing_value=str(existing_production),
            incoming_value=str(incoming_production),
            reason=reason,
            subsidiary=subsidiary,
            financial_year=financial_year,
            mine_type=mine_type,
        )
        quarantine_ids.append(qid)

    return safe_records, quarantine_ids
