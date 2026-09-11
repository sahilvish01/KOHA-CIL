"""
KOHA-CIL — Intelligent Query Router
Classifies incoming queries as STATISTICAL, QUALITATIVE or UNKNOWN.

Classification is primarily keyword/pattern-based (deterministic), ensuring
the router works even when Ollama is unavailable.
"""
from __future__ import annotations

import logging
import re
from typing import List

from models.schemas import QueryIntent

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Statistical indicator patterns
# ----------------------------------------------------------------
STATISTICAL_PATTERNS: List[str] = [
    r"\bproduction\b",
    r"\btarget\b",
    r"\bachievement\b",
    r"\bpercentage\b",
    r"\bmillion\s*tonne",
    r"\bMT\b",
    r"\bfy\s*20\d\d",
    r"\bfinancial\s*year\b",
    r"\bfy\b",
    r"\bstatistic",
    r"\bfigure",
    r"\bhow\s*much",
    r"\bhow\s*many",
    r"\btotal",
    r"\baggregate",
    r"\baverage",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\btrend",
    r"\bgrowth",
    r"\bdeclin",
    r"\bincrease",
    r"\bdecrease",
    r"\bECL\b",
    r"\bBCCL\b",
    r"\bCCL\b",
    r"\bSECL\b",
    r"\bMCL\b",
    r"\bsubsidiar",
    r"\bmine\s*type",
    r"\bunderground\b",
    r"\bopencast\b",
    r"\bquantit",
    r"\bdata\b",
    r"\bnumber\b",
    r"\brate\b",
    r"\bperform",
    r"\boutput\b",
    r"\byear",
    r"\bquarter",
]

# ----------------------------------------------------------------
# Qualitative indicator patterns
# ----------------------------------------------------------------
QUALITATIVE_PATTERNS: List[str] = [
    r"\bpolicy\b",
    r"\bpolicies\b",
    r"\bprocedure",
    r"\bguideline",
    r"\bregulation",
    r"\bframework",
    r"\bdescrib",
    r"\bexplain",
    r"\bwhat\s+is\b",
    r"\bwhat\s+are\b",
    r"\bwhat\s+does\b",
    r"\bhow\s+does\b",
    r"\bwhy\b",
    r"\bqualitative",
    r"\benvironmental",
    r"\bsafety\b",
    r"\bgeolog",
    r"\bobservation",
    r"\bsurvey",
    r"\bCSR\b",
    r"\bcorporate\s+social",
    r"\bdigital",
    r"\btransform",
    r"\bwater\s+management",
    r"\beffluent",
    r"\breclamation",
    r"\bafforestation",
    r"\bventilation",
    r"\bmine\s+safety",
    r"\bDGMS\b",
    r"\bnarrative",
    r"\breport\s+section",
    r"\bdocument",
    r"\bpassage",
    r"\bsummarise",
    r"\bsummarize",
    r"\bvision\s+2030",
    r"\bcoal\s+reserve",
    r"\bgeological\s+formation",
]


def _count_matches(text: str, patterns: List[str]) -> int:
    """Count how many patterns match the query (case-insensitive)."""
    text_lower = text.lower()
    return sum(1 for p in patterns if re.search(p, text_lower))


def classify(query: str) -> QueryIntent:
    """
    Classify a query as STATISTICAL, QUALITATIVE or UNKNOWN.

    Uses weighted keyword/regex matching. When scores are tied or both low,
    defaults to QUALITATIVE for safety (semantic retrieval is more general).
    """
    stat_score = _count_matches(query, STATISTICAL_PATTERNS)
    qual_score = _count_matches(query, QUALITATIVE_PATTERNS)

    logger.debug("Query classification — stat_score=%d, qual_score=%d, query='%s'", stat_score, qual_score, query[:80])

    if stat_score == 0 and qual_score == 0:
        return QueryIntent.UNKNOWN

    if stat_score > qual_score:
        return QueryIntent.STATISTICAL

    if qual_score >= stat_score:
        return QueryIntent.QUALITATIVE

    return QueryIntent.UNKNOWN
