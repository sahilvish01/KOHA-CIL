"""
KOHA-CIL — Backend Orchestrator
FastAPI application — main entry point.
All routes under /internal/* require the X-Internal-Auth header
(shared secret between the Security Gateway and this service).
"""
from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[1] / ".env")
except ImportError:
    pass

from config import INTERNAL_SECRET, BACKEND_PORT, UPLOAD_DIR, ensure_dirs
from database.connection import init_db
from database.seed import run_seed
from models.schemas import (
    LoginRequest, LoginResponse,
    QueryRequest, QueryResponse,
    ConflictReviewRequest, QuarantineRecord,
    AuditRecord, DashboardStats, HealthResponse,
    UserContext, UserRole,
)
from services import auth_service, audit_service, quarantine_service
from services.query_service import process_query
from agents import ollama_client
from agents.semantic_agent import build_index_from_db

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ================================================================
# Startup / Shutdown
# ================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database, seed data, probe Ollama on startup."""
    logger.info("KOHA-CIL Backend starting up…")
    ensure_dirs()
    init_db()
    run_seed()
    ollama_client.probe_ollama()
    try:
        build_index_from_db()
    except Exception as exc:
        logger.warning("Vector index build skipped: %s", exc)
    logger.info("KOHA-CIL Backend ready.")
    yield
    logger.info("KOHA-CIL Backend shutting down.")


# ================================================================
# App
# ================================================================

app = FastAPI(
    title="KOHA-CIL Backend Orchestrator",
    description="Enterprise Intelligence & Reporting Platform — Ministry of Coal / CIL",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================================================
# Security dependency
# ================================================================

def verify_internal_auth(x_internal_auth: Optional[str] = Header(default=None)) -> None:
    """Validate the shared internal secret header from the gateway."""
    if not x_internal_auth or x_internal_auth != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Internal authentication required.")


def extract_user_context(
    x_username: Optional[str] = Header(default=None),
    x_role: Optional[str] = Header(default=None),
    x_subsidiary: Optional[str] = Header(default=None),
    x_request_id: Optional[str] = Header(default=None),
) -> UserContext:
    """Build UserContext from trusted gateway-injected headers."""
    if not x_username or not x_role:
        raise HTTPException(status_code=400, detail="Missing user context headers.")
    try:
        role = UserRole(x_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {x_role}")
    return UserContext(
        username=x_username,
        role=role,
        subsidiary=x_subsidiary or None,
        request_id=x_request_id or str(uuid.uuid4()),
    )


def require_roles(user_ctx: UserContext, *roles: UserRole) -> None:
    """Apply sensitive-operation RBAC again at the backend boundary."""
    if user_ctx.role not in roles:
        raise HTTPException(status_code=403, detail="You do not have permission for this action.")


# ================================================================
# Health
# ================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Service health check."""
    from database.connection import get_db
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        service="backend",
        details={
            "database": "ok" if db_ok else "error",
            "ollama": "available" if ollama_client.is_available() else "unavailable",
        },
    )


# ================================================================
# Authentication (called by gateway only)
# ================================================================

@app.post("/internal/auth/verify", tags=["Internal"])
async def verify_credentials(
    body: LoginRequest,
    _: None = Depends(verify_internal_auth),
):
    """Verify user credentials. Returns user record or 401."""
    user = auth_service.verify_credentials(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    return {"success": True, "user": user}


# ================================================================
# Query
# ================================================================

@app.post("/internal/query", response_model=QueryResponse, tags=["Query"])
async def handle_query(
    body: QueryRequest,
    request: Request,
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
):
    """Process an intelligence query. Full router → agent → evidence → citation pipeline."""
    ip = request.client.host if request.client else None
    result = process_query(body.query, user_ctx, ip_address=ip)
    return result


# ================================================================
# Dashboard Stats
# ================================================================

@app.get("/internal/dashboard/stats", tags=["Dashboard"])
async def dashboard_stats(
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
):
    """Return summary statistics for the dashboard."""
    from database.connection import get_db

    with get_db() as conn:
        # Latest year totals per subsidiary
        latest_rows = conn.execute(
            """
            SELECT subsidiary, financial_year, production_mt, target_mt, achievement_percentage
            FROM production_statistics
            WHERE mine_type = 'TOTAL'
            ORDER BY financial_year DESC, subsidiary ASC
            """
        ).fetchall()

        # Group by subsidiary — take latest year only
        seen: dict = {}
        latest_production = []
        for r in latest_rows:
            s = r["subsidiary"]
            # RBAC: subsidiary officer only sees own subsidiary
            if user_ctx.role == UserRole.SUBSIDIARY_OFFICER and s != user_ctx.subsidiary:
                continue
            if s not in seen:
                seen[s] = True
                latest_production.append(dict(r))

        if user_ctx.role == UserRole.SUBSIDIARY_OFFICER:
            active_conflicts = conn.execute(
                "SELECT COUNT(*) AS cnt FROM quarantine_records WHERE status = 'PENDING_REVIEW' AND subsidiary = ?",
                (user_ctx.subsidiary,),
            ).fetchone()["cnt"]
            recent_queries = conn.execute(
                "SELECT COUNT(*) AS cnt FROM audit_log WHERE action = 'QUERY' AND username = ? AND timestamp >= datetime('now', '-7 days')",
                (user_ctx.username,),
            ).fetchone()["cnt"]
            recent_ingestions = conn.execute(
                "SELECT COUNT(*) AS cnt FROM ingestion_jobs WHERE submitted_by = ? AND created_at >= datetime('now', '-7 days')",
                (user_ctx.username,),
            ).fetchone()["cnt"]
        else:
            active_conflicts = quarantine_service.count_pending()
            recent_queries = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_log WHERE action = 'QUERY' AND timestamp >= datetime('now', '-7 days')"
            ).fetchone()["cnt"]
            recent_ingestions = conn.execute(
                "SELECT COUNT(*) as cnt FROM ingestion_jobs WHERE created_at >= datetime('now', '-7 days')"
            ).fetchone()["cnt"]

    subsidiaries = list(seen.keys()) if user_ctx.role == UserRole.HQ_OFFICER or user_ctx.role.value == "ADMIN" \
        else ([user_ctx.subsidiary] if user_ctx.subsidiary else [])

    return DashboardStats(
        total_subsidiaries=len(subsidiaries),
        subsidiaries=subsidiaries,
        latest_year_production=latest_production,
        active_conflicts=active_conflicts,
        recent_queries=recent_queries,
        recent_ingestions=recent_ingestions,
        system_health={
            "database": "ok",
            "ollama": "available" if ollama_client.is_available() else "unavailable",
        },
    )


# ================================================================
# Ingestion
# ================================================================

@app.post("/internal/ingest", tags=["Ingestion"])
async def ingest_document(
    file: UploadFile = File(...),
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
):
    """Accept a document upload and run the ingestion pipeline."""
    from database.connection import get_db
    from ingestion.ocr_engine import extract_text
    from ingestion.data_splitter import split_document
    from ingestion.conflict_detector import check_and_quarantine
    from ingestion.cache_manager import cache_document
    from agents.semantic_agent import index_policy
    import shutil

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    require_roles(user_ctx, UserRole.HQ_OFFICER, UserRole.ADMIN)
    safe_filename = Path(file.filename).name
    if not safe_filename or safe_filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid file name.")

    # Never use a client-controlled path or allow one upload to overwrite another.
    upload_path = Path(UPLOAD_DIR) / f"{uuid.uuid4().hex}_{safe_filename}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = upload_path.stat().st_size

    # Create job record
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO ingestion_jobs (filename, file_size, status, submitted_by) VALUES (?, ?, 'PROCESSING', ?)",
            (safe_filename, file_size, user_ctx.username),
        )
        job_id = cursor.lastrowid

    try:
        # Extract
        pages = extract_text(str(upload_path))
        ocr_pages = len(pages)

        # Cache document
        cache_document(safe_filename, pages)

        # Split
        stat_records, qual_records = split_document(safe_filename, pages)

        # Conflict check on stat records
        safe_stat, quarantine_ids = check_and_quarantine(stat_records)

        # Insert safe statistical records
        records_inserted = 0
        with get_db() as conn:
            for rec in safe_stat:
                if rec.get("production_mt") is None:
                    continue
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO production_statistics
                            (subsidiary, financial_year, mine_type, production_mt,
                             target_mt, achievement_percentage, data_label,
                             source_document, source_page, source_section)
                        VALUES (?, ?, ?, ?, ?, ?, 'INGESTED', ?, ?, ?)
                        """,
                        (
                            rec["subsidiary"], rec["financial_year"],
                            rec.get("mine_type", "TOTAL"), rec["production_mt"],
                            rec.get("target_mt", 0),
                            round(rec["production_mt"] / rec["target_mt"] * 100, 2) if rec.get("target_mt") else 0,
                            rec.get("source_document"), rec.get("source_page"),
                            rec.get("source_section"),
                        ),
                    )
                    records_inserted += 1
                except Exception as e:
                    logger.warning("Failed to insert stat record: %s", e)

            # Insert qualitative records
            for qual in qual_records:
                try:
                    cursor = conn.execute(
                        """
                        INSERT INTO qualitative_policies (topic, section, content, source_document, source_page, keywords)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (qual["topic"], qual.get("section"), qual["content"],
                         qual.get("source_document"), qual.get("source_page"),
                         qual.get("keywords")),
                    )
                    pol_id = cursor.lastrowid
                    # Index into vector store
                    index_policy(
                        pol_id, qual["topic"], qual.get("section", ""),
                        qual["content"], qual.get("source_document", ""),
                        qual.get("source_page", 0), qual.get("keywords", ""),
                    )
                    records_inserted += 1
                except Exception as e:
                    logger.warning("Failed to insert qual record: %s", e)

        # Update job
        with get_db() as conn:
            conn.execute(
                """UPDATE ingestion_jobs SET status='COMPLETED', ocr_pages=?, records_inserted=?,
                   conflicts_found=?, completed_at=datetime('now') WHERE id=?""",
                (ocr_pages, records_inserted, len(quarantine_ids), job_id),
            )

        audit_service.log_event(
            request_id=user_ctx.request_id,
            username=user_ctx.username,
            role=user_ctx.role.value,
            subsidiary=user_ctx.subsidiary,
            action="INGEST",
            query=f"Ingested: {safe_filename}",
            result_summary=f"Pages: {ocr_pages}, Records: {records_inserted}, Conflicts: {len(quarantine_ids)}",
            conflict_status="CONFLICT_DETECTED" if quarantine_ids else "CLEAN",
        )

        return {
            "success": True,
            "job_id": job_id,
            "filename": safe_filename,
            "ocr_pages": ocr_pages,
            "records_inserted": records_inserted,
            "conflicts_found": len(quarantine_ids),
            "quarantine_ids": quarantine_ids,
            "status": "COMPLETED",
        }

    except Exception as exc:
        logger.exception("Ingestion failed for %s", safe_filename)
        with get_db() as conn:
            conn.execute(
                "UPDATE ingestion_jobs SET status='FAILED', error_message=? WHERE id=?",
                (str(exc), job_id),
            )
        raise HTTPException(status_code=500, detail="Ingestion could not be completed. Review the server log for details.")


@app.get("/internal/ingestion/jobs", tags=["Ingestion"])
async def list_ingestion_jobs(
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
    limit: int = Query(default=20, le=100),
):
    """List recent ingestion jobs."""
    from database.connection import get_db
    with get_db() as conn:
        if user_ctx.role == UserRole.SUBSIDIARY_OFFICER:
            rows = conn.execute(
                "SELECT * FROM ingestion_jobs WHERE submitted_by = ? ORDER BY created_at DESC LIMIT ?",
                (user_ctx.username, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ingestion_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return {"jobs": [dict(r) for r in rows]}


# ================================================================
# Conflicts / Quarantine
# ================================================================

@app.get("/internal/conflicts", tags=["Conflicts"])
async def list_conflicts(
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
    status: Optional[str] = Query(default=None),
):
    """List quarantine records."""
    records = quarantine_service.get_all_quarantine(status=status)
    # Subsidiary officers only see records for their subsidiary
    if user_ctx.role == UserRole.SUBSIDIARY_OFFICER:
        records = [r for r in records if r.get("subsidiary") == user_ctx.subsidiary]
    return {"conflicts": records, "total": len(records)}


@app.post("/internal/conflicts/{record_id}/review", tags=["Conflicts"])
async def review_conflict(
    record_id: int,
    body: ConflictReviewRequest,
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
):
    """Approve or reject a quarantine record."""
    require_roles(user_ctx, UserRole.HQ_OFFICER, UserRole.ADMIN)
    try:
        updated = quarantine_service.review_quarantine(record_id, body.action, user_ctx.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or already reviewed.")

    audit_service.log_event(
        request_id=user_ctx.request_id,
        username=user_ctx.username,
        role=user_ctx.role.value,
        subsidiary=user_ctx.subsidiary,
        action=f"CONFLICT_{body.action}",
        result_summary=f"Quarantine record {record_id} {body.action} by {user_ctx.username}",
        conflict_status=body.action,
    )

    return {"success": True, "record_id": record_id, "status": body.action}


# ================================================================
# Audit Log
# ================================================================

@app.get("/internal/audit", tags=["Audit"])
async def get_audit_log(
    _: None = Depends(verify_internal_auth),
    user_ctx: UserContext = Depends(extract_user_context),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    username: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
):
    """Retrieve audit log entries."""
    # HQ officers see all; subsidiary officers see only their own entries
    filter_user = username
    if user_ctx.role == UserRole.SUBSIDIARY_OFFICER:
        filter_user = user_ctx.username

    records = audit_service.get_audit_log(
        limit=limit, offset=offset, username=filter_user, action=action
    )
    return {"audit_log": records, "total": len(records)}


# ================================================================
# Entrypoint
# ================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)
