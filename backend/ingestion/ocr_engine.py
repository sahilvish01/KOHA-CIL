"""Document preprocessing and text extraction for the ingestion pipeline."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _cv2_available = True
except ImportError:
    _cv2_available = False

try:
    import pytesseract
    from PIL import Image
    _tesseract_available = True
except ImportError:
    _tesseract_available = False


def _preprocess_image(image_path: str):
    if not _cv2_available:
        return None
    try:
        image = cv2.imread(image_path)
        if image is None:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)
        return cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    except Exception as exc:
        logger.warning("Image preprocessing failed: %s", exc)
        return None


def extract_text_from_image(image_path: str) -> Optional[str]:
    if not _tesseract_available:
        return None
    try:
        preprocessed = _preprocess_image(image_path)
        source = preprocessed if preprocessed is not None else image_path
        return pytesseract.image_to_string(source, config="--psm 6").strip()
    except Exception as exc:
        logger.error("OCR extraction failed for %s: %s", image_path, exc)
        return None


def _split_into_sections(text: str) -> List[dict]:
    if not text:
        return []
    sections, current_content, current_title = [], [], ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_header = ((len(stripped) < 80 and stripped.endswith(":")) or
                     (len(stripped) < 60 and stripped.isupper() and len(stripped) > 3))
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


def _ocr_pdf_page(pdf_path: str, page_number: int) -> str:
    """Rasterise an empty PDF page and OCR it when optional OCR tools exist."""
    if not _tesseract_available:
        return ""
    converter = shutil.which("pdftoppm")
    if not converter:
        logger.warning("PDF page %s has no text layer and pdftoppm is unavailable.", page_number)
        return ""
    try:
        with tempfile.TemporaryDirectory(prefix="koha-pdf-") as temp_dir:
            prefix = str(Path(temp_dir) / "page")
            subprocess.run(
                [converter, "-png", "-r", "220", "-f", str(page_number), "-l", str(page_number), pdf_path, prefix],
                check=True, capture_output=True, timeout=60,
            )
            image_path = next(Path(temp_dir).glob("page-*.png"), None)
            return extract_text_from_image(str(image_path)) if image_path else ""
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("PDF OCR fallback failed for page %s: %s", page_number, exc)
        return ""


def extract_text_from_pdf(pdf_path: str) -> List[dict]:
    """Extract each PDF page's text layer, using OCR only when it is empty."""
    try:
        import pypdf
    except ImportError:
        logger.error("PDF ingestion requires the pypdf package.")
        return []

    try:
        reader = pypdf.PdfReader(pdf_path)
        results = []
        for index, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            method = "PDF_TEXT"
            if not text:
                text = _ocr_pdf_page(pdf_path, index + 1).strip()
                method = "PDF_OCR" if text else "EMPTY_PAGE"
            results.append({"page_number": index + 1, "text": text,
                            "sections": _split_into_sections(text), "extraction_method": method})
        return results
    except Exception as exc:
        logger.warning("PDF extraction failed for %s: %s", pdf_path, exc)
        return []


def extract_text_from_delimited_file(file_path: str) -> List[dict]:
    """Read text, CSV and TSV uploads directly instead of treating them as OCR input."""
    try:
        raw = Path(file_path).read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
    except OSError as exc:
        logger.error("Unable to read text document %s: %s", file_path, exc)
        return []
    return [{"page_number": 1, "text": text.strip(), "sections": _split_into_sections(text),
             "extraction_method": "TEXT"}]


def extract_text(file_path: str) -> List[dict]:
    """Universal text extractor for PDF, image and text-based report uploads."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext in {".txt", ".csv", ".tsv"}:
        return extract_text_from_delimited_file(file_path)
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}:
        text = extract_text_from_image(file_path) or ""
        return [{"page_number": 1, "text": text, "sections": _split_into_sections(text),
                 "extraction_method": "OCR"}]
    logger.warning("Unsupported file type: %s", ext)
    return []