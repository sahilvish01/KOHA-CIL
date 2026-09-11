"""
KOHA-CIL — Ollama Client
Wraps calls to the local Ollama LLM service.
Provides a clean availability probe and graceful fallback.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Module-level availability flag (set during startup probe)
_ollama_available: bool = False


def probe_ollama() -> bool:
    """Check whether Ollama is running and the configured model is available.
    
    Sets and returns the module-level availability flag.
    """
    global _ollama_available
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            configured = OLLAMA_MODEL.split(":")[0]
            if configured in models:
                logger.info("Ollama available — model '%s' found.", OLLAMA_MODEL)
                _ollama_available = True
            else:
                logger.warning(
                    "Ollama running but model '%s' not found. Available: %s",
                    OLLAMA_MODEL,
                    models,
                )
                # Still mark available so we attempt generate (Ollama may auto-pull)
                _ollama_available = True
        else:
            logger.warning("Ollama probe returned HTTP %d", resp.status_code)
            _ollama_available = False
    except Exception as exc:
        logger.warning("Ollama unavailable: %s — using fallback mode.", exc)
        _ollama_available = False
    return _ollama_available


def is_available() -> bool:
    """Return current Ollama availability status."""
    return _ollama_available


def generate(prompt: str, system: str = "", timeout: float = 60.0) -> Optional[str]:
    """
    Send a prompt to Ollama and return the generated text.

    Returns None when Ollama is unavailable or the call fails.
    Callers must handle None and apply their own fallback logic.
    """
    if not _ollama_available:
        return None

    payload: dict = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 512},
    }
    if system:
        payload["system"] = system

    try:
        resp = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except httpx.TimeoutException:
        logger.warning("Ollama generate timed out — using fallback.")
        return None
    except Exception as exc:
        logger.error("Ollama generate error: %s", exc)
        return None


def synthesise_answer(query: str, evidence_chunks: list[str]) -> tuple[str, bool]:
    """
    Attempt to synthesise a grounded answer from retrieved evidence using Ollama.

    Returns (answer_text, fallback_used).
    When Ollama is unavailable, constructs a deterministic summary instead.
    """
    if not evidence_chunks:
        return "No sufficient evidence was found in the available KOHA-CIL knowledge base for this query.", True

    evidence_text = "\n\n---\n\n".join(f"[Evidence {i+1}]\n{chunk}" for i, chunk in enumerate(evidence_chunks))

    system_prompt = (
        "You are the KOHA-CIL Enterprise Intelligence assistant for the Ministry of Coal / "
        "Coal India Limited. Your role is to answer questions STRICTLY based on the evidence "
        "provided below. Do NOT add information that is not present in the evidence. "
        "If the evidence is insufficient to answer fully, say so clearly. "
        "Be concise, professional and factual."
    )

    user_prompt = (
        f"EVIDENCE:\n{evidence_text}\n\n"
        f"QUESTION: {query}\n\n"
        "Based only on the evidence above, provide a clear, concise, professional answer. "
        "Do not fabricate any details not present in the evidence."
    )

    response = generate(user_prompt, system=system_prompt)

    if response:
        return response, False

    # Fallback: construct a simple keyword-based summary
    combined = " ".join(evidence_chunks[:2])
    sentences = [s.strip() for s in combined.replace("\n", " ").split(".") if len(s.strip()) > 20]
    summary = ". ".join(sentences[:4]) + "." if sentences else evidence_chunks[0][:500]
    return f"[Fallback Mode — Local AI Unavailable]\n\n{summary}", True
