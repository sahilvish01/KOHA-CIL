"""
KOHA-CIL — Citation Service
Converts raw evidence rows into structured, source-accurate citation objects.
Never fabricates missing source metadata.
"""
from __future__ import annotations

from typing import List

from models.schemas import Citation, EvidenceRow


def build_citations(evidence: List[EvidenceRow]) -> List[Citation]:
    """
    Convert evidence rows to citation objects.
    Only populates fields that are actually present in the evidence.
    Never invents page numbers, cells or document names.
    """
    citations: List[Citation] = []
    seen: set = set()

    for ev in evidence:
        # Deduplicate by (document, page, cell)
        key = (ev.source_document, ev.source_page, ev.source_cell)
        if key in seen:
            continue
        seen.add(key)

        citation = Citation(
            source_document=ev.source_document or None,
            page=ev.source_page or None,
            section=ev.source_section or None,
            cell=ev.source_cell or None,
            # Provide a short evidence snippet (first 300 chars)
            evidence=_evidence_snippet(ev),
        )
        citations.append(citation)

    return citations


def _evidence_snippet(ev: EvidenceRow) -> str:
    """Return a short evidence snippet from the row."""
    if ev.content:
        return ev.content[:300] + ("…" if len(ev.content) > 300 else "")

    if ev.production_mt is not None:
        return (
            f"{ev.subsidiary} {ev.financial_year} {ev.mine_type}: "
            f"Production {ev.production_mt:.1f} MT / Target {ev.target_mt:.1f} MT "
            f"({ev.achievement_percentage:.1f}%)"
        )
    return ""
