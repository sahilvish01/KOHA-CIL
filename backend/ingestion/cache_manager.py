"""
KOHA-CIL — Cache Manager
Writes and reads Markdown-cached representations of ingested documents.
Preserves document/page/section structure in the cache files.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from config import CACHE_DIR

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    """Sanitise a document name for use as a filename."""
    name = re.sub(r'[^\w\-.]', '_', name)
    return name.replace(".pdf", ".md").replace(".PDF", ".md")


def cache_document(document_name: str, pages: list[dict]) -> str:
    """
    Write a Markdown cache file for a document.

    pages: list of dicts with keys: page_number, sections (list of {title, content})
    Returns the cache file path.
    """
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(document_name)
    cache_path = Path(CACHE_DIR) / filename

    lines = [f"# {document_name}\n", f"**Cached Document — KOHA-CIL Knowledge Base**\n\n"]
    for page in pages:
        lines.append(f"---\n\n## Page {page.get('page_number', '?')}\n\n")
        for section in page.get("sections", []):
            title = section.get("title", "")
            content = section.get("content", "")
            if title:
                lines.append(f"### {title}\n\n")
            if content:
                lines.append(f"{content}\n\n")

    cache_path.write_text("".join(lines), encoding="utf-8")
    logger.info("Cached document: %s → %s", document_name, cache_path)
    return str(cache_path)


def read_cache(document_name: str) -> Optional[str]:
    """
    Read a cached Markdown document.
    Returns the content string or None if not cached.
    """
    filename = _safe_filename(document_name)
    cache_path = Path(CACHE_DIR) / filename

    if not cache_path.exists():
        return None

    content = cache_path.read_text(encoding="utf-8")
    logger.info("Cache hit for document: %s", document_name)
    return content


def is_cached(document_name: str) -> bool:
    """Check whether a document has a cache entry."""
    filename = _safe_filename(document_name)
    return (Path(CACHE_DIR) / filename).exists()


def list_cached_documents() -> list[str]:
    """List all cached document filenames."""
    cache_dir = Path(CACHE_DIR)
    if not cache_dir.exists():
        return []
    return [f.name for f in cache_dir.glob("*.md")]
