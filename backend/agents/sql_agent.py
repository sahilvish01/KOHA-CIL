"""
KOHA-CIL — SQL Agent
Processes STATISTICAL queries against the SQLite production_statistics table.
All arithmetic is performed deterministically by the database — no LLM arithmetic.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from database.connection import get_db
from models.schemas import EvidenceRow, UserContext

logger = logging.getLogger(__name__)

# ---- Known subsidiary aliases ----
SUBSIDIARY_ALIASES = {
    "ecl": "ECL",
    "eastern coalfields": "ECL",
    "bccl": "BCCL",
    "bharat coking coal": "BCCL",
    "ccl": "CCL",
    "central coalfields": "CCL",
    "secl": "SECL",
    "south eastern coalfields": "SECL",
    "mcl": "MCL",
    "mahanadi coalfields": "MCL",
}

# ---- Mine type aliases ----
MINE_TYPE_ALIASES = {
    "underground": "UNDERGROUND",
    "ug": "UNDERGROUND",
    "opencast": "OPENCAST",
    "oc": "OPENCAST",
    "surface": "OPENCAST",
    "total": "TOTAL",
    "overall": "TOTAL",
    "combined": "TOTAL",
}

# ---- Financial year patterns ----
# Matches: FY2024, FY 2024, FY2023-24, 2023-24, 2024
FY_PATTERN = re.compile(
    r"\b(?:fy\s*)?(\d{4})(?:[–\-](\d{2,4}))?\b", re.IGNORECASE
)


def _extract_subsidiary(query: str) -> Optional[str]:
    """Extract subsidiary name from query text."""
    lower = query.lower()
    for alias, canonical in SUBSIDIARY_ALIASES.items():
        if alias in lower:
            return canonical
    return None


def _extract_mine_type(query: str) -> Optional[str]:
    """Extract mine type from query text."""
    lower = query.lower()
    for alias, canonical in MINE_TYPE_ALIASES.items():
        if alias in lower:
            return canonical
    return None


def _extract_financial_year(query: str) -> Optional[str]:
    """Extract and normalise financial year from query text."""
    for match in FY_PATTERN.finditer(query):
        year_start = int(match.group(1))
        year_end_raw = match.group(2)
        if year_end_raw:
            if len(year_end_raw) == 2:
                year_end = year_start + 1 if int(year_end_raw) == (year_start + 1) % 100 else year_start + 1
            else:
                year_end = int(year_end_raw)
        else:
            year_end = year_start + 1
        return f"FY{year_start}-{str(year_end)[-2:]}"
    return None


def _apply_rbac_filter(subsidiary_filter: Optional[str], user_ctx: UserContext) -> Optional[str]:
    """Enforce RBAC: subsidiary officers can only see their own subsidiary."""
    from models.schemas import UserRole
    if user_ctx.role == UserRole.SUBSIDIARY_OFFICER:
        return user_ctx.subsidiary  # Always restrict to their own
    # HQ_OFFICER/ADMIN can see any (or all if no filter)
    return subsidiary_filter


def execute_query(query: str, user_ctx: UserContext) -> Tuple[List[EvidenceRow], str]:
    """
    Parse the query, build parameterised SQL, execute and return evidence rows.

    Returns (evidence_rows, answer_text).
    All calculations are performed by SQLite — no LLM arithmetic.
    """
    subsidiary = _extract_subsidiary(query)
    mine_type = _extract_mine_type(query)
    financial_year = _extract_financial_year(query)

    # Enforce RBAC
    subsidiary = _apply_rbac_filter(subsidiary, user_ctx)

    conditions: list = []
    params: list = []

    if subsidiary:
        conditions.append("subsidiary = ?")
        params.append(subsidiary)

    if mine_type:
        conditions.append("mine_type = ?")
        params.append(mine_type)
    else:
        # Default to TOTAL unless user specified a type
        conditions.append("mine_type = 'TOTAL'")

    if financial_year:
        conditions.append("financial_year = ?")
        params.append(financial_year)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT
            subsidiary,
            financial_year,
            mine_type,
            production_mt,
            target_mt,
            achievement_percentage,
            source_document,
            source_page,
            source_cell,
            source_section,
            data_label
        FROM production_statistics
        WHERE {where_clause}
        ORDER BY financial_year DESC, subsidiary ASC
        LIMIT 50
    """

    logger.debug("SQL Agent — query='%s' subsidiary=%s mine_type=%s fy=%s",
                 query[:80], subsidiary, mine_type, financial_year)

    try:
        with get_db() as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:
        logger.error("SQL Agent DB error: %s", exc)
        return [], "A database error occurred while processing your query."

    if not rows:
        return [], ""

    evidence = [EvidenceRow(**dict(r)) for r in rows]

    # Build deterministic textual answer
    answer = _format_answer(evidence, query, subsidiary, financial_year, mine_type)
    return evidence, answer


def _format_answer(
    evidence: List[EvidenceRow],
    query: str,
    subsidiary: Optional[str],
    financial_year: Optional[str],
    mine_type: Optional[str],
) -> str:
    """Format a professional textual answer from SQL evidence rows."""
    if not evidence:
        return "No sufficient evidence was found in the available KOHA-CIL knowledge base for this query."

    lines = []

    # Single subsidiary + single year
    if len(evidence) == 1:
        r = evidence[0]
        lines.append(
            f"**{r.subsidiary}** production for **{r.financial_year}** "
            f"({r.mine_type} mines): **{r.production_mt:.1f} MT** "
            f"against a target of {r.target_mt:.1f} MT "
            f"(achievement: {r.achievement_percentage:.1f}%)."
        )
        lines.append(f"\n*Source: {r.source_document or 'N/A'}, Page {r.source_page or 'N/A'}, Cell {r.source_cell or 'N/A'}*")
        if r.data_label == "DEMO DATA":
            lines.append("\n⚠ This is DEMO DATA — not official statistics.")
        return "\n".join(lines)

    # Multiple rows — tabular summary
    lines.append("Production figures from the KOHA-CIL knowledge base:\n")
    lines.append("| Subsidiary | Year | Type | Production (MT) | Target (MT) | Achievement |")
    lines.append("|---|---|---|---|---|---|")
    for r in evidence:
        lines.append(
            f"| {r.subsidiary} | {r.financial_year} | {r.mine_type} "
            f"| {r.production_mt:.1f} | {r.target_mt:.1f} | {r.achievement_percentage:.1f}% |"
        )

    demo_rows = [r for r in evidence if r.data_label == "DEMO DATA"]
    if demo_rows:
        lines.append("\n⚠ All figures shown are **DEMO DATA** — not official statistics.")

    return "\n".join(lines)
