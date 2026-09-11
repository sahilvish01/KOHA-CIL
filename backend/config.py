"""
KOHA-CIL — Centralised Backend Configuration
All settings are loaded from environment variables with safe defaults.
"""
import os
from pathlib import Path

# ---- Base Paths ----
BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / ".." / "data" / "koha_cil.db"))).parent

# ---- Service Ports ----
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

# ---- Database ----
DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "koha_cil.db"))

# ---- Upload / Storage Dirs ----
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads"))
QUARANTINE_DIR: str = os.getenv("QUARANTINE_DIR", str(DATA_DIR / "quarantine"))
CACHE_DIR: str = os.getenv("CACHE_DIR", str(DATA_DIR / "cache"))
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma"))

# ---- Security ----
INTERNAL_SECRET: str = os.getenv("INTERNAL_SECRET", "koha-cil-internal-shared-secret")

# ---- Logging ----
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ---- Semantic Retrieval ----
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
SEMANTIC_TOP_K: int = int(os.getenv("SEMANTIC_TOP_K", "5"))

# ---- JWT (needed only if backend validates tokens directly — normally done by gateway) ----
JWT_SECRET: str = os.getenv("JWT_SECRET", "koha-cil-dev-jwt-secret-change-in-production")


def ensure_dirs() -> None:
    """Create required runtime directories if they do not exist."""
    for d in [UPLOAD_DIR, QUARANTINE_DIR, CACHE_DIR, CHROMA_PERSIST_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)
