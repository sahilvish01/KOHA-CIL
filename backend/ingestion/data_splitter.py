"""Classify extracted report content into statistical and qualitative records."""
from __future__ import annotations

import csv
import io
import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)
SUBSIDIARY_PATTERN = re.compile(r"\b(ECL|BCCL|CCL|SECL|MCL)\b", re.IGNORECASE)
FY_PATTERN = re.compile(r"(?:FY\s*)?(\d{4})\s*[–-]\s*(\d{2,4})", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?![\w.])")
STAT_ROW_PATTERN = re.compile(r"\b(ECL|BCCL|CCL|SECL|MCL)\b.*?\b((?:FY\s*)?\d{4}\s*[–-]\s*\d{2,4})\b", re.IGNORECASE)
STAT_KEYWORDS = {"production", "target", "achievement", "mt", "million tonne", "output", "offtake", "excavation", "fy", "financial year"}
QUAL_KEYWORDS = {"policy", "procedure", "guideline", "regulation", "observed", "survey", "geological", "environmental", "safety", "csr", "digital", "description", "overview", "background"}


def _is_qualitative(text: str) -> bool:
    return sum(keyword in text.lower() for keyword in QUAL_KEYWORDS) >= 1 and len(text.split()) > 30


def split_document(document_name: str, pages: List[dict]) -> Tuple[List[dict], List[dict]]:
    stat_records, qual_records = [], []
    for page in pages:
        page_num = page.get("page_number", 0)
        raw_text = page.get("text", "")
        # Always parse raw page content.  Text/CSV reports usually form a single
        # section, which previously prevented their statistical rows being parsed.
        if raw_text:
            stat_records.extend(_extract_stat_rows(raw_text, document_name, page_num, "Document data"))
        for section in page.get("sections", []):
            title, content = section.get("title", ""), section.get("content", "")
            if content and _is_qualitative(content):
                qual_records.append({"topic": title or "General", "section": title, "content": content,
                                     "source_document": document_name, "source_page": page_num,
                                     "keywords": _extract_keywords(content)})
        if raw_text and not page.get("sections") and _is_qualitative(raw_text):
            qual_records.append({"topic": "General", "section": None, "content": raw_text[:2000],
                                 "source_document": document_name, "source_page": page_num,
                                 "keywords": _extract_keywords(raw_text)})
    unique, seen = [], set()
    for record in stat_records:
        key = tuple(record[field] for field in ("subsidiary", "financial_year", "mine_type", "production_mt", "target_mt", "source_document", "source_page"))
        if key not in seen:
            seen.add(key)
            unique.append(record)
    logger.info("Data split for '%s': %d statistical, %d qualitative records", document_name, len(unique), len(qual_records))
    return unique, qual_records


def _extract_stat_rows(text: str, document_name: str, page_num: int, section: str) -> List[dict]:
    rows = _extract_delimited_rows(text, document_name, page_num, section)
    if rows:
        return rows
    # pypdf frequently returns visual table cells on separate lines.  Collapsing
    # whitespace preserves their reading order while allowing one row to span lines.
    normalised = " ".join(text.split())
    matches = list(STAT_ROW_PATTERN.finditer(normalised))
    for index, match in enumerate(matches):
        fy = _normalise_fy(match.group(2))
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(normalised)
        remainder = normalised[match.end(2):next_start]
        values = _numbers(remainder)
        if not fy or not values:
            continue
        production = _labelled_number(remainder, "production")
        if production is None:
            production = values[0]
        target = _labelled_number(remainder, "target")
        if target is None and len(values) > 1:
            target = values[1]
        rows.append(_record(match.group(1).upper(), fy, _mine_type(remainder), production, target, document_name, page_num, section))
    return rows


def _extract_delimited_rows(text: str, document_name: str, page_num: int, section: str) -> List[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    delimiter = "\t" if "\t" in lines[0] else ("|" if "|" in lines[0] else ",")
    try:
        reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
        headers = reader.fieldnames or []
    except csv.Error:
        return []
    keys = {_header_key(header): header for header in headers if header}
    subsidiary_key = _find_header(keys, "subsidiary")
    fy_key = _find_header(keys, "financialyear", "fy", "year")
    production_key = _find_header(keys, "productionmt", "production")
    if not (subsidiary_key and fy_key and production_key):
        return []
    mine_key, target_key = _find_header(keys, "minetype", "mine"), _find_header(keys, "targetmt", "target")
    rows = []
    for item in reader:
        subsidiary = SUBSIDIARY_PATTERN.search(item.get(subsidiary_key, ""))
        fy, production = _normalise_fy(item.get(fy_key, "")), _to_number(item.get(production_key, ""))
        if not (subsidiary and fy and production is not None):
            continue
        rows.append(_record(subsidiary.group(1).upper(), fy, _mine_type(item.get(mine_key, "")) if mine_key else "TOTAL", production,
                            _to_number(item.get(target_key, "")) if target_key else None, document_name, page_num, section))
    return rows


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _find_header(headers: dict, *names: str) -> Optional[str]:
    return next((headers[name] for name in names if name in headers), None)


def _normalise_fy(value: str) -> Optional[str]:
    match = FY_PATTERN.search(value or "")
    return f"FY{match.group(1)}-{match.group(2)[-2:]}" if match else None


def _numbers(value: str) -> List[float]:
    return [float(number.replace(",", "")) for number in NUMBER_PATTERN.findall(value or "")]


def _to_number(value: str) -> Optional[float]:
    values = _numbers(value)
    return values[0] if values else None


def _labelled_number(text: str, label: str) -> Optional[float]:
    match = re.search(rf"{label}(?:\s*\([^)]*\))?\s*[:=]?\s*({NUMBER_PATTERN.pattern})", text, re.IGNORECASE)
    return _to_number(match.group(1)) if match else None


def _mine_type(value: str) -> str:
    lower = (value or "").lower()
    if "opencast" in lower or "open cast" in lower:
        return "OPENCAST"
    if "underground" in lower:
        return "UNDERGROUND"
    return "TOTAL"


def _record(subsidiary: str, financial_year: str, mine_type: str, production: float, target: Optional[float], document_name: str, page_num: int, section: str) -> dict:
    return {"subsidiary": subsidiary, "financial_year": financial_year, "mine_type": mine_type, "production_mt": production, "target_mt": target, "source_document": document_name, "source_page": page_num, "source_section": section}


def _extract_keywords(text: str) -> str:
    return ",".join(keyword for keyword in (STAT_KEYWORDS | QUAL_KEYWORDS) if keyword in text.lower())