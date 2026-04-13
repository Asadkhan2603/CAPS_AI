from io import BytesIO
import logging

import docx
import pdfplumber

from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_file_content(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith('.pdf'):
        return _parse_pdf(content)
    if lower.endswith('.docx'):
        return _parse_docx(content)
    if lower.endswith('.txt') or lower.endswith('.md'):
        return content.decode('utf-8', errors='ignore')
    return ''


def _parse_pdf(content: bytes) -> str:
    texts = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            if text:
                texts.append(text)
    extracted = '\n'.join(texts)
    if _should_run_ocr(extracted):
        ocr_text = _run_ocr(content)
        if ocr_text:
            if extracted:
                return f"{extracted}\n{ocr_text}"
            return ocr_text
    return extracted


def _should_run_ocr(extracted_text: str) -> bool:
    if not settings.ocr_enabled:
        return False
    if not extracted_text:
        return True
    return len(extracted_text.strip()) < settings.ocr_min_chars


def _run_ocr(content: bytes) -> str:
    if not settings.ocr_enabled or settings.ocr_provider == "disabled":
        return ""
    # OCR scaffolding placeholder. Wire provider implementation here.
    _ = content
    logger.info(
        "OCR enabled but provider not configured; skipping OCR. provider=%s languages=%s",
        settings.ocr_provider,
        settings.ocr_languages,
    )
    return ""


def _parse_docx(content: bytes) -> str:
    document = docx.Document(BytesIO(content))
    return '\n'.join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
