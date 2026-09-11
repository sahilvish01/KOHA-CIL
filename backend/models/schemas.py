"""
KOHA-CIL — Pydantic Schemas
All request/response models used across the backend.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ================================================================
# Enumerations
# ================================================================

class QueryIntent(str, Enum):
    STATISTICAL = "STATISTICAL"
    QUALITATIVE = "QUALITATIVE"
    UNKNOWN = "UNKNOWN"


class ProcessingPath(str, Enum):
    SQL = "SQL"
    SEMANTIC = "SEMANTIC"
    FALLBACK = "FALLBACK"
    NONE = "NONE"


class ConflictStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class UserRole(str, Enum):
    HQ_OFFICER = "HQ_OFFICER"
    SUBSIDIARY_OFFICER = "SUBSIDIARY_OFFICER"
    ADMIN = "ADMIN"


# ================================================================
# Trusted User Context (injected by gateway via headers)
# ================================================================

class UserContext(BaseModel):
    username: str
    role: UserRole
    subsidiary: Optional[str] = None
    request_id: str = ""


# ================================================================
# Authentication
# ================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    # returned as a plain user dict so gateway can build JWT
    user: Optional[dict] = None


# ================================================================
# Query
# ================================================================

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


class Citation(BaseModel):
    source_document: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    table: Optional[str] = None
    cell: Optional[str] = None
    evidence: Optional[str] = None


class EvidenceRow(BaseModel):
    subsidiary: Optional[str] = None
    financial_year: Optional[str] = None
    mine_type: Optional[str] = None
    production_mt: Optional[float] = None
    target_mt: Optional[float] = None
    achievement_percentage: Optional[float] = None
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    source_cell: Optional[str] = None
    source_section: Optional[str] = None
    data_label: Optional[str] = None
    content: Optional[str] = None  # for qualitative evidence


class QueryResponse(BaseModel):
    success: bool
    query: str
    intent: QueryIntent
    answer: str
    evidence: List[EvidenceRow] = []
    citations: List[Citation] = []
    processing_path: ProcessingPath
    fallback_used: bool = False
    request_id: str = ""
    data_label: Optional[str] = None   # "DEMO DATA" if applicable


# ================================================================
# Ingestion
# ================================================================

class IngestionStatus(BaseModel):
    job_id: int
    filename: str
    status: str
    ocr_pages: int = 0
    records_inserted: int = 0
    conflicts_found: int = 0
    error_message: Optional[str] = None
    submitted_by: str
    created_at: str
    completed_at: Optional[str] = None


# ================================================================
# Quarantine / Conflict
# ================================================================

class QuarantineRecord(BaseModel):
    id: int
    source_document: str
    field_name: str
    existing_value: str
    incoming_value: str
    subsidiary: Optional[str] = None
    financial_year: Optional[str] = None
    mine_type: Optional[str] = None
    reason: str
    status: ConflictStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str


class ConflictReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    reviewer: str


# ================================================================
# Audit
# ================================================================

class AuditRecord(BaseModel):
    id: int
    timestamp: str
    request_id: str
    username: str
    role: str
    subsidiary: Optional[str] = None
    action: str
    query: Optional[str] = None
    intent: Optional[str] = None
    result_summary: Optional[str] = None
    citation_count: int = 0
    conflict_status: Optional[str] = None
    ip_address: Optional[str] = None


# ================================================================
# Dashboard
# ================================================================

class DashboardStats(BaseModel):
    total_subsidiaries: int
    subsidiaries: List[str]
    latest_year_production: List[dict]
    active_conflicts: int
    recent_queries: int
    recent_ingestions: int
    system_health: dict


# ================================================================
# Health
# ================================================================

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str = "1.0.0"
    details: Optional[dict] = None
