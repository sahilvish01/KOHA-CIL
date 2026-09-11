"""
KOHA-CIL — Data Splitter
Classifies extracted document content into STATISTICAL and QUALITATIVE records.
Prepares structured dicts ready for DB insertion and semantic indexing.
"""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Regex to detect production table rows
# e.g. "ECL  FY2023-24  TOTAL  35.9  38.5  93.2"
STAT_ROW_PATTERN = re.compile(
    r"\b(ECL|BCCL|CCL|SECL|MCL)\b.*?"
    r"\b(FY\d{4}[–\-]\d{2,4}|\d{4}[–\-]\d{2,4})\b.*?"
    r"\b(\d{1,3}(?:\.\d{1,2})?)\b",
    re.IGNORECASE,
)

STAT_KEYWORDS = {
    "production", "target", "achievement", "mt", "million tonne",
    "output", "offtake", "excavation", "fy", "financial year",
}

QUAL_KEYWORDS = {
    "policy", "procedure", "guideline", "regulation", "observed",
    "survey", "geological", "environmental", "safety", "csr",
    "digital", "description", "overview", "background",
}


def _is_statistical(text: str) -> bool:
    """Heuristically determine if a text block contains statistical data."""
    lower = text.lower()
    stat_hits = sum(1 for kw in STAT_KEYWORDS if kw in lower)
    has_numbers = len(re.findall(r"\b\d{1,3}(?:\.\d{1,2})?\b", text)) >= 3
    has_subsidiary = bool(re.search(r"\b(ECL|BCCL|CCL|SECL|MCL)\b", text, re.IGNORECASE))
    return stat_hits >= 2 and (has_numbers or has_subsidiary)


def _is_qualitative(text: str) -> bool:
    """Heuristically determine if a text block is qualitative/narrative."""
    lower = text.lower()
    qual_hits = sum(1 for kw in QUAL_KEYWORDS if kw in lower)
    word_count = len(text.split())
    return qual_hits >= 1 and word_count > 30


def split_document(
    document_name: str,
    pages: List[dict],
) -> Tuple[List[dict], List[dict]]:
    """
    Split extracted page content into statistical and qualitative records.

    Returns:
        (statistical_records, qualitative_records)
    
    Each statistical_record: {subsidiary, financial_year, mine_type,
        production_mt, target_mt, source_document, source_page, source_section}
    Each qualitative_record: {topic, section, content, source_document, source_page}
    """
    stat_records: List[dict] = []
    qual_records: List[dict] = []

    for page in pages:
        page_num = page.get("page_number", 0)
        sections = page.get("sections", [])

        for section in sections:
            title = section.get("title", "")
            content = section.get("content", "")

            if not content:
                continue

            if _is_statistical(content):
                # Attempt to extract structured rows
                extracted = _extract_stat_rows(content, document_name, page_num, title)
                stat_records.extend(extracted)

            if _is_qualitative(content):
                qual_records.append({
                    "topic": title or "General",
                    "section": title,
                    "content": content,
                    "source_document": document_name,
                    "source_page": page_num,
                    "keywords": _extract_keywords(content),
                })

        # Also check raw page text
        raw_text = page.get("text", "")
        if raw_text and not sections:
            if _is_qualitative(raw_text):
                qual_records.append({
                    "topic": "General",
                    "section": None,
                    "content": raw_text[:2000],
                    "source_document": document_name,
                    "source_page": page_num,
                    "keywords": _extract_keywords(raw_text),
                })

    logger.info(
        "Data split for '%s': %d statistical, %d qualitative records",
        document_name, len(stat_records), len(qual_records),
    )
    return stat_records, qual_records


def _extract_stat_rows(
    text: str, document_name: str, page_num: int, section: str
) -> List[dict]:
    """Attempt to parse structured production rows from text."""
    rows = []
    for match in STAT_ROW_PATTERN.finditer(text):
        subsidiary = match.group(1).upper()
        fy_raw = match.group(2)
        # Normalise FY
        fy = fy_raw if fy_raw.upper().startswith("FY") else f"FY{fy_raw}"
        try:
            value = float(match.group(3))
        except ValueError:
            continue
        rows.append({
            "subsidiary": subsidiary,
            "financial_year": fy,
            "mine_type": "TOTAL",  # Default; refine if 'underground'/'opencast' nearby
            "production_mt": value,
            "target_mt": None,
            "source_document": document_name,
            "source_page": page_num,
            "source_section": section,
        })
    return rows


def _extract_keywords(text: str) -> str:
    """Extract comma-separated keywords from text."""
    all_kw = STAT_KEYWORDS | QUAL_KEYWORDS
    lower = text.lower()
    found = [kw for kw in all_kw if kw in lower]
    return ",".join(found[:10])
