"""
KOHA-CIL — Semantic Agent
Handles QUALITATIVE queries by retrieving relevant evidence from the
qualitative_policies table using keyword/TF-IDF matching.

When ChromaDB + sentence-transformers are installed, upgrades to full
vector-similarity search automatically. Falls back to keyword search otherwise.
"""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

from database.connection import get_db
from models.schemas import EvidenceRow
from agents.ollama_client import synthesise_answer

logger = logging.getLogger(__name__)

# ---- Try to import vector store dependencies ----
_vector_store_available = False
_chroma_collection = None

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

    _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    _chroma_client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    _chroma_collection = _chroma_client.get_or_create_collection(
        name="koha_cil_qualitative",
        metadata={"hnsw:space": "cosine"},
    )
    _vector_store_available = True
    logger.info("ChromaDB vector store initialised successfully.")
except ImportError:
    logger.info("ChromaDB/sentence-transformers not installed — using keyword fallback.")
except Exception as exc:
    logger.warning("Vector store init error: %s — using keyword fallback.", exc)


def _keyword_search(query: str, top_k: int = 5) -> List[dict]:
    """
    SQLite full-text keyword search across qualitative_policies.
    Returns dicts with all policy fields.
    """
    # Extract meaningful words (>3 chars, no stop words)
    stop_words = {"what", "is", "are", "the", "a", "an", "in", "of", "for",
                  "and", "or", "to", "how", "does", "do", "describe", "explain"}
    words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()) if w not in stop_words]

    if not words:
        # Return all policies as fallback
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM qualitative_policies LIMIT ?", (top_k,)).fetchall()
        return [dict(r) for r in rows]

    # Build a LIKE query for each word against content + keywords
    conditions = []
    params = []
    for word in words[:8]:  # limit to 8 keywords
        conditions.append("(LOWER(content) LIKE ? OR LOWER(keywords) LIKE ? OR LOWER(topic) LIKE ?)")
        params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])

    where = " OR ".join(conditions)
    sql = f"SELECT * FROM qualitative_policies WHERE {where} LIMIT ?"
    params.append(top_k)

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _vector_search(query: str, top_k: int = 5) -> List[dict]:
    """Vector similarity search using ChromaDB + sentence-transformers."""
    if not _vector_store_available or _chroma_collection is None:
        return _keyword_search(query, top_k)

    try:
        embedding = _embedding_model.encode(query).tolist()
        results = _chroma_collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, _chroma_collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        if not results or not results.get("documents"):
            return _keyword_search(query, top_k)

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        return [{"content": doc, **meta} for doc, meta in zip(docs, metas)]
    except Exception as exc:
        logger.warning("Vector search error: %s — falling back to keyword.", exc)
        return _keyword_search(query, top_k)


def index_policy(policy_id: int, topic: str, section: str, content: str,
                 source_document: str, source_page: int, keywords: str) -> None:
    """Add or update a policy record in the ChromaDB vector store."""
    if not _vector_store_available or _chroma_collection is None:
        return
    try:
        embedding = _embedding_model.encode(content).tolist()
        _chroma_collection.upsert(
            ids=[f"policy_{policy_id}"],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "topic": topic,
                "section": section or "",
                "source_document": source_document or "",
                "source_page": source_page or 0,
                "keywords": keywords or "",
            }],
        )
    except Exception as exc:
        logger.warning("Failed to index policy %d: %s", policy_id, exc)


def build_index_from_db() -> None:
    """Index all qualitative policies from DB into ChromaDB (idempotent)."""
    if not _vector_store_available:
        return
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM qualitative_policies").fetchall()
    for row in rows:
        r = dict(row)
        index_policy(
            r["id"], r["topic"], r.get("section", ""),
            r["content"], r.get("source_document", ""),
            r.get("source_page", 0), r.get("keywords", ""),
        )
    logger.info("Indexed %d qualitative policies into ChromaDB.", len(rows))


def retrieve(query: str, top_k: int = 5) -> Tuple[List[EvidenceRow], str, bool]:
    """
    Retrieve qualitative evidence for a query.

    Returns (evidence_rows, answer_text, fallback_used).
    """
    if _vector_store_available:
        raw_results = _vector_search(query, top_k)
    else:
        raw_results = _keyword_search(query, top_k)

    if not raw_results:
        no_evidence_msg = (
            "No sufficient evidence was found in the available KOHA-CIL "
            "knowledge base for this query."
        )
        return [], no_evidence_msg, True

    # Build evidence rows
    evidence_rows: List[EvidenceRow] = []
    evidence_texts: List[str] = []

    for r in raw_results:
        ev = EvidenceRow(
            content=r.get("content", ""),
            source_document=r.get("source_document"),
            source_page=r.get("source_page"),
            source_section=r.get("section") or r.get("topic"),
        )
        evidence_rows.append(ev)
        evidence_texts.append(r.get("content", ""))

    # Synthesise answer (uses Ollama if available, else deterministic fallback)
    answer, fallback_used = synthesise_answer(query, evidence_texts)

    return evidence_rows, answer, fallback_used
