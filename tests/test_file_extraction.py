import io

import pytest
from docx import Document
from pypdf import PdfWriter

import app


class _FakeUpload(io.BytesIO):
    """Minimal stand-in for Streamlit's UploadedFile: file-like (seek/read,
    as pypdf/python-docx require) plus the .name attribute extract_file()
    checks."""

    def __init__(self, name: str, data: bytes):
        super().__init__(data)
        self.name = name


def _docx_bytes(paragraphs):
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_bytes(num_pages: int = 1):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_txt_happy_path():
    upload = _FakeUpload("resume.txt", "Hello world".encode("utf-8"))
    assert app.extract_file(upload) == "Hello world"


def test_md_happy_path():
    upload = _FakeUpload("resume.md", "# Heading".encode("utf-8"))
    assert app.extract_file(upload) == "# Heading"


def test_txt_invalid_utf8_ignored():
    upload = _FakeUpload("resume.txt", b"Hello \xff\xfe world")
    result = app.extract_file(upload)
    assert "Hello" in result and "world" in result


def test_unsupported_extension_raises():
    upload = _FakeUpload("resume.exe", b"whatever")
    with pytest.raises(ValueError, match="Supported files"):
        app.extract_file(upload)


def test_oversized_file_rejected(monkeypatch):
    monkeypatch.setattr(app, "MAX_UPLOAD_BYTES", 10)
    upload = _FakeUpload("resume.txt", b"this is definitely more than 10 bytes")
    with pytest.raises(ValueError, match="too large"):
        app.extract_file(upload)


def test_valid_docx_extracts_text():
    data = _docx_bytes(["Line one", "Line two"])
    upload = _FakeUpload("resume.docx", data)
    result = app.extract_file(upload)
    assert result == "Line one\nLine two"


def test_corrupt_docx_raises_sanitized_error():
    upload = _FakeUpload("resume.docx", b"not a real docx file, just garbage bytes")
    with pytest.raises(ValueError, match="Could not read this DOCX file"):
        app.extract_file(upload)


def test_valid_pdf_extracts_without_raising():
    data = _pdf_bytes(num_pages=1)
    upload = _FakeUpload("resume.pdf", data)
    result = app.extract_file(upload)
    assert isinstance(result, str)


def test_corrupt_pdf_raises_sanitized_error():
    upload = _FakeUpload("resume.pdf", b"%PDF-1.4 not actually valid pdf content")
    with pytest.raises(ValueError, match="Could not read this PDF"):
        app.extract_file(upload)


def test_pdf_page_cap_enforced(monkeypatch):
    monkeypatch.setattr(app, "MAX_PDF_PAGES", 2)
    data = _pdf_bytes(num_pages=3)
    upload = _FakeUpload("resume.pdf", data)
    with pytest.raises(ValueError, match="too many pages"):
        app.extract_file(upload)
