import logging
import time
from base64 import b64encode
from dataclasses import dataclass
from io import BytesIO

import docx
import pdfplumber
from openai import OpenAI

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
            "result_state": "disabled",
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
            "result_state": "empty",
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
            "result_state": "success",
        }


class OpenAiDocumentOcrAdapter(BaseOcrAdapter):
    provider_name = "openai_responses"

    def extract_text(self, *, filename: str, content: bytes, page_count: int, languages: list[str]) -> dict:
        if not settings.openai_api_key:
            return {
                "text": "",
                "provider": self.provider_name,
                "attempted": False,
                "chars_added": 0,
                "extraction_confidence": 0.0,
                "error": "openai_api_key_not_configured",
                "result_state": "provider_not_configured",
            }

        client = OpenAI(api_key=settings.openai_api_key, timeout=float(settings.ocr_timeout_seconds))
        encoded = b64encode(content).decode("ascii")
        prompt = (
            "Extract readable text from this document for plagiarism review. "
            "Return plain text only with paragraph breaks preserved. "
            f"Prefer languages: {', '.join(languages) or 'eng'}."
        )
        response = client.responses.create(
            model=settings.ocr_openai_model or settings.openai_model,
            max_output_tokens=max(256, int(settings.ocr_max_output_tokens)),
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_file",
                            "filename": filename,
                            "file_data": f"data:application/pdf;base64,{encoded}",
                        },
                    ],
                }
            ],
        )
        output_text = str(getattr(response, "output_text", "") or "").strip()
        chars_added = len(output_text)
        if not output_text:
            return {
                "text": "",
                "provider": self.provider_name,
                "attempted": True,
                "chars_added": 0,
                "extraction_confidence": 0.0,
                "error": "empty_ocr_response",
                "result_state": "empty",
            }
        confidence = min(0.94, 0.42 + min(chars_added / 2400.0, 0.42) + min(page_count / 30.0, 0.1))
        return {
            "text": output_text,
            "provider": self.provider_name,
            "attempted": True,
            "chars_added": chars_added,
            "extraction_confidence": round(confidence, 3),
            "error": None,
            "result_state": "success",
        }


def _ocr_provider_registry() -> dict[str, BaseOcrAdapter]:
    return {
        "disabled": BaseOcrAdapter(),
        "noop": LoggedNoopOcrAdapter(),
        "mock_echo": MockEchoOcrAdapter(),
        "openai_responses": OpenAiDocumentOcrAdapter(),
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
                "ocr_result_state": "not_needed" if text else "empty",
                "ocr_retry_count": 0,
                "ocr_timeout_seconds": int(settings.ocr_timeout_seconds),
                "ocr_error": None,
                "ocr_retry_guidance": _ocr_retry_guidance(
                    low_text_reason="empty_extraction" if not text else None,
                    ocr_result_state="not_needed" if text else "empty",
                    ocr_provider=None,
                ),
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
                "ocr_result_state": "not_needed" if text.strip() else "empty",
                "ocr_retry_count": 0,
                "ocr_timeout_seconds": int(settings.ocr_timeout_seconds),
                "ocr_error": None,
                "ocr_retry_guidance": _ocr_retry_guidance(
                    low_text_reason="empty_extraction" if not text.strip() else None,
                    ocr_result_state="not_needed" if text.strip() else "empty",
                    ocr_provider=None,
                ),
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
            "ocr_result_state": "unsupported",
            "ocr_retry_count": 0,
            "ocr_timeout_seconds": int(settings.ocr_timeout_seconds),
            "ocr_error": None,
            "ocr_retry_guidance": _ocr_retry_guidance(
                low_text_reason="unsupported_file_type",
                ocr_result_state="unsupported",
                ocr_provider=None,
            ),
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
        "result_state": "not_needed" if not low_text_reason else "not_run",
        "retry_count": 0,
        "timeout_seconds": int(settings.ocr_timeout_seconds),
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
            "ocr_result_state": ocr_result.get("result_state"),
            "ocr_retry_count": int(ocr_result.get("retry_count") or 0),
            "ocr_timeout_seconds": int(ocr_result.get("timeout_seconds") or settings.ocr_timeout_seconds),
            "ocr_error": ocr_result.get("error"),
            "ocr_retry_guidance": _ocr_retry_guidance(
                low_text_reason=_infer_low_text_reason(extracted) or low_text_reason,
                ocr_result_state=ocr_result.get("result_state"),
                ocr_provider=ocr_result.get("provider"),
            ),
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
            "result_state": "disabled",
            "retry_count": 0,
            "timeout_seconds": int(settings.ocr_timeout_seconds),
        }
    provider_key = str(settings.ocr_provider or "disabled").strip().lower()
    provider = _ocr_provider_registry().get(provider_key)
    if provider is None:
        logger.warning(
            "OCR enabled but provider '%s' is not registered; falling back to noop adapter",
            provider_key,
        )
        provider = LoggedNoopOcrAdapter()

    max_attempts = max(1, int(settings.ocr_max_retries) + 1)
    last_error = None
    last_state = "failed"
    last_result: dict | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = provider.extract_text(
                filename=filename,
                content=content,
                page_count=page_count,
                languages=list(settings.ocr_languages or []),
            )
            if not isinstance(result, dict):
                raise ValueError("invalid_ocr_adapter_response")
            normalized = {
                "text": str(result.get("text") or ""),
                "provider": result.get("provider") or provider.provider_name,
                "attempted": bool(result.get("attempted", True)),
                "chars_added": int(result.get("chars_added") or 0),
                "extraction_confidence": max(0.0, min(float(result.get("extraction_confidence") or 0.0), 1.0)),
                "error": result.get("error"),
                "result_state": str(result.get("result_state") or ("success" if result.get("text") else "empty")),
                "retry_count": attempt - 1,
                "timeout_seconds": int(settings.ocr_timeout_seconds),
            }
            last_result = normalized
            last_error = normalized.get("error")
            last_state = str(normalized.get("result_state") or "failed")
            if normalized["text"] or last_state in {"success", "provider_not_configured", "unsupported", "disabled"}:
                return normalized
            if attempt < max_attempts:
                time.sleep(max(0.0, float(settings.ocr_retry_backoff_seconds)))
        except TimeoutError as exc:
            last_error = str(exc)[:300] or "ocr_timeout"
            last_state = "timeout"
            if attempt < max_attempts:
                time.sleep(max(0.0, float(settings.ocr_retry_backoff_seconds)))
        except Exception as exc:
            last_error = str(exc)[:300] or "ocr_failed"
            last_state = "failed"
            if attempt < max_attempts:
                time.sleep(max(0.0, float(settings.ocr_retry_backoff_seconds)))

    if last_result is not None:
        return {
            **last_result,
            "error": last_error,
            "result_state": last_state,
            "retry_count": max_attempts - 1,
        }
    return {
        "text": "",
        "provider": provider.provider_name,
        "attempted": True,
        "chars_added": 0,
        "extraction_confidence": 0.0,
        "error": last_error,
        "result_state": last_state,
        "retry_count": max_attempts - 1,
        "timeout_seconds": int(settings.ocr_timeout_seconds),
    }


def _ocr_retry_guidance(*, low_text_reason: str | None, ocr_result_state: str | None, ocr_provider: str | None) -> str | None:
    if not low_text_reason and ocr_result_state in {"success", "not_needed"}:
        return None
    if ocr_result_state == "provider_not_configured":
        return "Configure the OCR provider before treating this PDF as reliable review evidence."
    if ocr_result_state == "timeout":
        return "OCR timed out. Retry with a smaller or clearer PDF before using similarity evidence from this file."
    if ocr_result_state == "failed":
        return "OCR failed. Re-upload a text-searchable PDF or retry OCR before using this as strong evidence."
    if ocr_result_state == "empty":
        return "OCR added no usable text. Treat this as insufficient evidence until a clearer upload is available."
    if low_text_reason:
        provider_label = ocr_provider or "configured OCR"
        return (
            f"Low extracted text remains after {provider_label}. "
            "Treat this submission as insufficient evidence until extraction quality improves."
        )
    return None


def _parse_docx(content: bytes) -> str:
    document = docx.Document(BytesIO(content))
    return '\n'.join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
