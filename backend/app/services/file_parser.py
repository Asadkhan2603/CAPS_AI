import logging
from dataclasses import dataclass
from io import BytesIO

import docx
import pdfplumber

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ParsedFileResult:
    text: str
    extraction_diagnostics: dict


class BaseOcrAdapter:
    provider_name = "disabled"

    def extract_text(self, *, filename: str, content: bytes, page_count: int, languages: list[str]) -> dict:
        _ = (filename, content, page_count, languages)
        return {
            "text": "",
            "provider": self.provider_name,
            "attempted": False,
            "chars_added": 0,
            "extraction_confidence": 0.0,
            "error": None,
        }


class LoggedNoopOcrAdapter(BaseOcrAdapter):
    provider_name = "noop"

    def extract_text(self, *, filename: str, content: bytes, page_count: int, languages: list[str]) -> dict:
        _ = (content, page_count)
        logger.info(
            "OCR adapter noop invoked for filename=%s provider=%s languages=%s",
            filename,
            settings.ocr_provider,
            languages,
        )
        return {
            "text": "",
            "provider": self.provider_name,
            "attempted": True,
            "chars_added": 0,
            "extraction_confidence": 0.0,
            "error": None,
        }


class MockEchoOcrAdapter(BaseOcrAdapter):
    provider_name = "mock_echo"

    def extract_text(self, *, filename: str, content: bytes, page_count: int, languages: list[str]) -> dict:
        _ = content
        mock_text = (
            f"Mock OCR placeholder for {filename}. "
            f"Pages detected: {page_count}. Languages: {', '.join(languages) or 'eng'}."
        )
        return {
            "text": mock_text,
            "provider": self.provider_name,
            "attempted": True,
            "chars_added": len(mock_text),
            "extraction_confidence": 0.35,
            "error": None,
        }


def _ocr_provider_registry() -> dict[str, BaseOcrAdapter]:
    return {
        "disabled": BaseOcrAdapter(),
        "noop": LoggedNoopOcrAdapter(),
        "mock_echo": MockEchoOcrAdapter(),
    }


def parse_file_content(filename: str, content: bytes) -> str:
    return parse_file_content_with_diagnostics(filename, content).text


def parse_file_content_with_diagnostics(filename: str, content: bytes) -> ParsedFileResult:
    lower = filename.lower()
    if lower.endswith('.pdf'):
        return _parse_pdf(filename, content)
    if lower.endswith('.docx'):
        text = _parse_docx(content)
        return ParsedFileResult(
            text=text,
            extraction_diagnostics={
                "ocr_attempted": False,
                "ocr_provider": None,
                "ocr_chars_added": 0,
                "page_count": None,
                "extraction_confidence": 1.0 if text else 0.0,
                "low_text_reason": "empty_extraction" if not text else None,
                "parser": "docx",
            },
        )
    if lower.endswith('.txt') or lower.endswith('.md'):
        text = content.decode('utf-8', errors='ignore')
        return ParsedFileResult(
            text=text,
            extraction_diagnostics={
                "ocr_attempted": False,
                "ocr_provider": None,
                "ocr_chars_added": 0,
                "page_count": None,
                "extraction_confidence": 1.0 if text.strip() else 0.0,
                "low_text_reason": "empty_extraction" if not text.strip() else None,
                "parser": "text",
            },
        )
    return ParsedFileResult(
        text='',
        extraction_diagnostics={
            "ocr_attempted": False,
            "ocr_provider": None,
            "ocr_chars_added": 0,
            "page_count": None,
            "extraction_confidence": 0.0,
            "low_text_reason": "unsupported_file_type",
            "parser": "unsupported",
        },
    )


def _parse_pdf(filename: str, content: bytes) -> ParsedFileResult:
    texts = []
    page_count = 0
    with pdfplumber.open(BytesIO(content)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ''
            if text:
                texts.append(text)
    extracted = '\n'.join(texts)
    low_text_reason = _infer_low_text_reason(extracted)
    ocr_result = {
        "text": "",
        "provider": None,
        "attempted": False,
        "chars_added": 0,
        "extraction_confidence": 0.0 if low_text_reason else 1.0,
        "error": None,
    }
    if _should_run_ocr(extracted):
        ocr_result = _run_ocr(filename=filename, content=content, page_count=page_count)
        ocr_text = str(ocr_result.get("text") or "")
        if ocr_text:
            if extracted:
                extracted = f"{extracted}\n{ocr_text}"
            else:
                extracted = ocr_text
    extraction_confidence = ocr_result.get("extraction_confidence")
    if not isinstance(extraction_confidence, (int, float)):
        extraction_confidence = 1.0 if extracted.strip() else 0.0
    return ParsedFileResult(
        text=extracted,
        extraction_diagnostics={
            "ocr_attempted": bool(ocr_result.get("attempted")),
            "ocr_provider": ocr_result.get("provider"),
            "ocr_chars_added": int(ocr_result.get("chars_added") or 0),
            "page_count": page_count,
            "extraction_confidence": round(float(extraction_confidence), 3),
            "low_text_reason": _infer_low_text_reason(extracted) or low_text_reason,
            "parser": "pdf",
            "ocr_error": ocr_result.get("error"),
        },
    )


def _should_run_ocr(extracted_text: str) -> bool:
    if not settings.ocr_enabled:
        return False
    if not extracted_text:
        return True
    return len(extracted_text.strip()) < settings.ocr_min_chars


def _infer_low_text_reason(extracted_text: str) -> str | None:
    stripped = (extracted_text or "").strip()
    if not stripped:
        return "empty_pdf_text"
    if len(stripped) < settings.ocr_min_chars:
        return "below_ocr_min_chars"
    return None


def _run_ocr(*, filename: str, content: bytes, page_count: int) -> dict:
    if not settings.ocr_enabled:
        return {
            "text": "",
            "provider": None,
            "attempted": False,
            "chars_added": 0,
            "extraction_confidence": 0.0,
            "error": None,
        }
    provider_key = str(settings.ocr_provider or "disabled").strip().lower()
    provider = _ocr_provider_registry().get(provider_key)
    if provider is None:
        logger.warning(
            "OCR enabled but provider '%s' is not registered; falling back to noop adapter",
            provider_key,
        )
        provider = LoggedNoopOcrAdapter()
    result = provider.extract_text(
        filename=filename,
        content=content,
        page_count=page_count,
        languages=list(settings.ocr_languages or []),
    )
    if not isinstance(result, dict):
        return {
            "text": "",
            "provider": provider.provider_name,
            "attempted": True,
            "chars_added": 0,
            "extraction_confidence": 0.0,
            "error": "invalid_ocr_adapter_response",
        }
    return result


def _parse_docx(content: bytes) -> str:
    document = docx.Document(BytesIO(content))
    return '\n'.join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
