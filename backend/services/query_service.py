"""
KOHA-CIL — Query Service
Orchestrates the full query processing pipeline:
  Router → SQL/Semantic Agent → Evidence → Citation → Audit → Response
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from agents.intelligent_router import classify
from agents.sql_agent import execute_query
from agents.semantic_agent import retrieve
from services.citation_service import build_citations
from services import audit_service
from models.schemas import (
    QueryIntent, ProcessingPath, QueryResponse, UserContext, EvidenceRow
)

logger = logging.getLogger(__name__)

NO_EVIDENCE_MSG = (
    "No sufficient evidence was found in the available KOHA-CIL knowledge base for this query."
)


def process_query(query: str, user_ctx: UserContext, ip_address: Optional[str] = None) -> QueryResponse:
    """
    Full query processing pipeline.
    Returns a QueryResponse with evidence, citations and audit metadata.
    """
    request_id = user_ctx.request_id or str(uuid.uuid4())

    # ---- 1. Classify intent ----
    intent = classify(query)
    logger.info("Query intent: %s — '%s'", intent.value, query[:80])

    evidence = []
    answer = NO_EVIDENCE_MSG
    processing_path = ProcessingPath.NONE
    fallback_used = False

    # ---- 2. Route to appropriate agent ----
    if intent == QueryIntent.STATISTICAL:
        evidence, answer = execute_query(query, user_ctx)
        processing_path = ProcessingPath.SQL

        if not evidence:
            answer = NO_EVIDENCE_MSG
            processing_path = ProcessingPath.FALLBACK
            fallback_used = True

    elif intent == QueryIntent.QUALITATIVE:
        evidence, answer, fallback_used = retrieve(query)
        processing_path = ProcessingPath.SEMANTIC if not fallback_used else ProcessingPath.FALLBACK

        if not evidence:
            answer = NO_EVIDENCE_MSG

    else:  # UNKNOWN — try semantic as a sensible default
        evidence, answer, fallback_used = retrieve(query)
        processing_path = ProcessingPath.SEMANTIC if evidence else ProcessingPath.FALLBACK
        if not evidence:
            answer = NO_EVIDENCE_MSG
            fallback_used = True

    # ---- 3. Build citations ----
    citations = build_citations(evidence)

    # ---- 4. Check for DEMO DATA label ----
    data_labels = {ev.data_label for ev in evidence if ev.data_label}
    data_label = "DEMO DATA" if "DEMO DATA" in data_labels else None

    # ---- 5. Audit ----
    audit_service.log_event(
        request_id=request_id,
        username=user_ctx.username,
        role=user_ctx.role.value,
        subsidiary=user_ctx.subsidiary,
        action="QUERY",
        query=query,
        intent=intent.value,
        result_summary=answer[:200] if answer else None,
        citation_count=len(citations),
        ip_address=ip_address,
    )

    return QueryResponse(
        success=True,
        query=query,
        intent=intent,
        answer=answer,
        evidence=evidence,
        citations=citations,
        processing_path=processing_path,
        fallback_used=fallback_used,
        request_id=request_id,
        data_label=data_label,
    )
