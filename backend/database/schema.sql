-- ============================================================
-- KOHA-CIL Enterprise Intelligence Platform
-- Database Schema
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---- Users ----
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('HQ_OFFICER', 'SUBSIDIARY_OFFICER', 'ADMIN')),
    subsidiary      TEXT,          -- NULL for HQ / ADMIN; ECL/BCCL/CCL/SECL/MCL for subsidiary users
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---- Production Statistics ----
CREATE TABLE IF NOT EXISTS production_statistics (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    subsidiary              TEXT NOT NULL CHECK (subsidiary IN ('ECL','BCCL','CCL','SECL','MCL')),
    financial_year          TEXT NOT NULL,          -- e.g. "FY2023-24"
    mine_type               TEXT NOT NULL CHECK (mine_type IN ('UNDERGROUND','OPENCAST','TOTAL')),
    production_mt           REAL NOT NULL,          -- production in million tonnes
    target_mt               REAL NOT NULL,          -- target in million tonnes
    achievement_percentage  REAL NOT NULL,          -- computed % (production/target*100)
    data_label              TEXT NOT NULL DEFAULT 'DEMO DATA',   -- DEMO DATA or OFFICIAL
    source_document         TEXT,
    source_page             INTEGER,
    source_cell             TEXT,
    source_section          TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_prod_stats
    ON production_statistics (subsidiary, financial_year, mine_type);

-- ---- Qualitative Policies ----
CREATE TABLE IF NOT EXISTS qualitative_policies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    section         TEXT,
    content         TEXT NOT NULL,
    source_document TEXT,
    source_page     INTEGER,
    keywords        TEXT,           -- comma-separated keyword list
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---- Audit Log ----
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    request_id      TEXT NOT NULL,
    username        TEXT NOT NULL,
    role            TEXT NOT NULL,
    subsidiary      TEXT,
    action          TEXT NOT NULL,
    query           TEXT,
    intent          TEXT,
    result_summary  TEXT,
    citation_count  INTEGER DEFAULT 0,
    conflict_status TEXT,
    ip_address      TEXT
);

-- ---- Quarantine Records ----
CREATE TABLE IF NOT EXISTS quarantine_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_document TEXT NOT NULL,
    field_name      TEXT NOT NULL,
    existing_value  TEXT NOT NULL,
    incoming_value  TEXT NOT NULL,
    subsidiary      TEXT,
    financial_year  TEXT,
    mine_type       TEXT,
    reason          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING_REVIEW'
                        CHECK (status IN ('PENDING_REVIEW','APPROVED','REJECTED')),
    reviewed_by     TEXT,
    reviewed_at     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---- Ingestion Jobs ----
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT NOT NULL,
    file_size       INTEGER,
    status          TEXT NOT NULL DEFAULT 'PROCESSING'
                        CHECK (status IN ('PROCESSING','COMPLETED','FAILED','PARTIAL')),
    ocr_pages       INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    conflicts_found  INTEGER DEFAULT 0,
    error_message   TEXT,
    submitted_by    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT
);
