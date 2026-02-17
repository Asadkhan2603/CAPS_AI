from io import BytesIO

import docx
import pdfplumber


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
    return '\n'.join(texts)


def _parse_docx(content: bytes) -> str:
    document = docx.Document(BytesIO(content))
    return '\n'.join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
