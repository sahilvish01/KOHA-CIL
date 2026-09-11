"""
KOHA-CIL — OCR Engine
Document preprocessing and text extraction pipeline.
Uses OpenCV for image preprocessing and pytesseract for OCR.
Gracefully degrades if these optional dependencies are not installed.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---- Optional imports ----
try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False
    logger.info("OpenCV not installed — image preprocessing disabled.")

try:
    import pytesseract
    from PIL import Image
    _tesseract_available = True
except ImportError:
    _tesseract_available = False
    logger.info("pytesseract/Pillow not installed — OCR disabled.")

try:
    from PIL import Image as PILImage
    _pil_available = True
except ImportError:
    _pil_available = False


def _preprocess_image(image_path: str):
    """
    Apply OpenCV preprocessing for improved OCR accuracy:
    1. Grayscale conversion
    2. Contrast enhancement (CLAHE)
    3. Noise reduction (Gaussian blur)
    4. Adaptive thresholding / Otsu binarisation
    """
    if not _cv2_available:
        return None
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Gaussian noise reduction
        denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # Otsu binarisation
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binary
    except Exception as exc:
        logger.warning("Image preprocessing failed: %s", exc)
        return None


def extract_text_from_image(image_path: str) -> Optional[str]:
    """Extract text from a single image file using tesseract."""
    if not _tesseract_available:
        return None

    preprocessed = _preprocess_image(image_path) if _cv2_available else None

    try:
        if preprocessed is not None:
            text = pytesseract.image_to_string(preprocessed, config="--psm 6")
        else:
            text = pytesseract.image_to_string(image_path, config="--psm 6")
        return text.strip()
    except Exception as exc:
        logger.error("OCR extraction failed for %s: %s", image_path, exc)
        return None


def extract_text_from_pdf(pdf_path: str) -> List[dict]:
    """
    Extract text from a PDF document, page by page.
    
    Returns a list of page dicts: {page_number, text, sections}.
    Falls back to simulated extraction if pytesseract is unavailable.
    """
    results = []

    # Try pypdf / PyPDF2 for text PDFs first (no OCR needed)
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            results.append({
                "page_number": i + 1,
                "text": text.strip(),
                "sections": _split_into_sections(text),
                "extraction_method": "PDF_TEXT",
            })
        if results:
            logger.info("Extracted %d pages from PDF (text mode): %s", len(results), pdf_path)
            return results
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pypdf extraction failed: %s — attempting OCR.", exc)

    # If text extraction failed, log that OCR is needed
    logger.warning(
        "PDF text extraction unavailable for %s. "
        "Install pytesseract + poppler for OCR support.",
        pdf_path,
    )
    # Return a minimal placeholder so the ingestion pipeline continues
    return [{
        "page_number": 1,
        "text": f"[OCR unavailable — manual extraction required for {Path(pdf_path).name}]",
        "sections": [],
        "extraction_method": "UNAVAILABLE",
    }]


def _split_into_sections(text: str) -> List[dict]:
    """Split extracted text into rough sections based on common headers."""
    if not text:
        return []

    sections = []
    # Split on lines that look like headers (all caps, or short with colon)
    lines = text.split("\n")
    current_title = ""
    current_content: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Heuristic: a "header" line is short, ends with ':' or is mostly uppercase
        is_header = (
            (len(stripped) < 80 and stripped.endswith(":")) or
            (len(stripped) < 60 and stripped.isupper() and len(stripped) > 3)
        )
        if is_header:
            if current_content:
                sections.append({"title": current_title, "content": " ".join(current_content)})
                current_content = []
            current_title = stripped.rstrip(":")
        else:
            current_content.append(stripped)

    if current_content:
        sections.append({"title": current_title, "content": " ".join(current_content)})

    return sections


def extract_text(file_path: str) -> List[dict]:
    """
    Universal text extractor — dispatches to PDF or image extractor.
    Returns list of page dicts.
    """
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}:
        text = extract_text_from_image(file_path)
        return [{
            "page_number": 1,
            "text": text or "",
            "sections": _split_into_sections(text or ""),
            "extraction_method": "OCR",
        }]
    else:
        logger.warning("Unsupported file type: %s", ext)
        return []
