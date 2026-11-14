from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest
from docx import Document

from ingestion.upload_pipeline import (
    DocumentExtractionError,
    extract_upload_batch,
    extract_uploaded_document,
    validate_upload_batch,
    UploadValidationError,
)


class Upload(BytesIO):
    def __init__(self, name: str, content: bytes):
        super().__init__(content)
        self.name = name
        self.size = len(content)


class FakeOCR:
    def __init__(self, text="OCR extracted text"):
        self.text = text
        self.images = []
        self.pages = []

    def image_to_text(self, image_bytes, language):
        self.images.append((image_bytes, language))
        return self.text

    def pdf_page_to_image(self, pdf_bytes, page_number):
        self.pages.append((pdf_bytes, page_number))
        return b"page image bytes"


def make_docx() -> bytes:
    document = Document()
    document.add_paragraph("The system shall support a document requirement.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Condition"
    table.rows[0].cells[1].text = "Expected behavior"
    target = BytesIO()
    document.save(target)
    return target.getvalue()


def test_accepts_multiple_documents_with_size_limits():
    batch = [Upload("first.pdf", b"1234"), Upload("second.docx", b"12345")]
    accepted = validate_upload_batch(
        batch, max_files=2, max_file_bytes=5, max_batch_bytes=9
    )
    assert accepted == batch


@pytest.mark.parametrize(
    "batch,limits,message",
    [
        ([Upload("a.pdf", b"x"), Upload("b.pdf", b"x")], (1, 5, 10), "maximum is 1"),
        ([Upload("a.pdf", b"123456")], (2, 5, 10), "per-file limit"),
        ([Upload("a.pdf", b"1234"), Upload("b.pdf", b"1234")], (2, 5, 7), "batch limit"),
        ([Upload("a.txt", b"x")], (2, 5, 10), "Unsupported file type"),
    ],
)
def test_rejects_invalid_upload_batches(batch, limits, message):
    with pytest.raises(UploadValidationError, match=message):
        validate_upload_batch(
            batch,
            max_files=limits[0],
            max_file_bytes=limits[1],
            max_batch_bytes=limits[2],
        )


def test_extracts_docx_paragraphs_and_tables_without_disk_files():
    result = extract_uploaded_document(Upload("spec.docx", make_docx()))
    assert "The system shall support" in result.text
    assert "Condition | Expected behavior" in result.text
    assert result.file_name == "spec.docx"
    assert "SOURCE DOCUMENT: spec.docx" in result.as_context_text()
    assert result.ocr_page_count == 0


def test_extract_upload_batch_keeps_each_source_and_upload_order():
    uploads = [
        Upload("first.docx", make_docx()),
        Upload("second.docx", make_docx()),
    ]
    progress = []

    results = extract_upload_batch(
        uploads,
        max_files=3,
        max_file_bytes=1024 * 1024,
        max_batch_bytes=2 * 1024 * 1024,
        progress=progress.append,
    )

    assert [result.file_name for result in results] == [
        "first.docx",
        "second.docx",
    ]
    assert all("SOURCE DOCUMENT:" in result.as_context_text() for result in results)
    assert any("Reading file 1 of 2" in item for item in progress)
    assert any("Reading file 2 of 2" in item for item in progress)


def test_extracts_image_with_injected_ocr_backend():
    ocr = FakeOCR("Readable image content")
    result = extract_uploaded_document(
        Upload("diagram.png", b"image bytes"),
        ocr_backend=ocr,
        ocr_language="eng+fra",
    )
    assert result.text == "Readable image content"
    assert result.extraction_method == "OCR"
    assert result.ocr_page_count == 1
    assert ocr.images == [(b"image bytes", "eng+fra")]


def test_image_without_ocr_reports_setup_instructions():
    with pytest.raises(DocumentExtractionError, match="requires OCR"):
        extract_uploaded_document(Upload("scan.jpg", b"image bytes"))


def test_scanned_pdf_page_is_rendered_then_ocrd():
    class Page:
        def extract_text(self):
            return ""

    class FakeReader:
        is_encrypted = False
        pages = [Page()]

    ocr = FakeOCR("Recognized scanned page")
    progress = []
    with patch("ingestion.upload_pipeline.PdfReader", return_value=FakeReader()), patch(
        "ingestion.upload_pipeline._page_has_images", return_value=True
    ):
        result = extract_uploaded_document(
            Upload("scan.pdf", b"pdf bytes"),
            ocr_backend=ocr,
            progress=progress.append,
        )

    assert "PAGE 1\nRecognized scanned page" in result.text
    assert result.ocr_page_count == 1
    assert result.page_count == 1
    assert ocr.pages == [(b"pdf bytes", 1)]
    assert progress == ["scan.pdf: processed page 1 of 1"]


def test_encrypted_pdf_is_rejected_before_processing():
    class EncryptedReader:
        is_encrypted = True

    with patch(
        "ingestion.upload_pipeline.PdfReader", return_value=EncryptedReader()
    ):
        with pytest.raises(DocumentExtractionError, match="password-protected"):
            extract_uploaded_document(Upload("locked.pdf", b"pdf bytes"))
