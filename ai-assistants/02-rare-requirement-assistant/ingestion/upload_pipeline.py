"""Bounded, provenance-preserving extraction for requirement uploads."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from docx import Document as WordDocument
from PyPDF2 import PdfReader


SUPPORTED_UPLOAD_EXTENSIONS = frozenset(
    {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
)


class UploadValidationError(ValueError):
    """Raised when a batch exceeds configured intake limits."""


class DocumentExtractionError(RuntimeError):
    """Raised when a supported document cannot be safely extracted."""


class OCRBackend(Protocol):
    def image_to_text(self, image_bytes: bytes, language: str) -> str: ...

    def pdf_page_to_image(
        self, pdf_bytes: bytes, page_number: int
    ) -> bytes: ...


@dataclass(frozen=True)
class ExtractedDocument:
    file_name: str
    text: str
    file_size_bytes: int
    page_count: int | None
    ocr_page_count: int = 0

    @property
    def extraction_method(self) -> str:
        if Path(self.file_name).suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            return "OCR"
        if self.ocr_page_count:
            return "Text extraction with OCR"
        return "Text extraction"

    def as_context_text(self) -> str:
        return f"SOURCE DOCUMENT: {self.file_name}\n{self.text.strip()}"


def validate_upload_batch(
    uploaded_files: Iterable[Any],
    *,
    max_files: int,
    max_file_bytes: int,
    max_batch_bytes: int,
) -> list[Any]:
    """Validate counts, aggregate size, extensions, and filenames up front."""
    files = list(uploaded_files or [])
    if not files:
        raise UploadValidationError("Upload at least one requirement document.")
    if len(files) > max_files:
        raise UploadValidationError(
            f"This batch has {len(files)} files; the configured maximum is {max_files}."
        )

    total_bytes = 0
    for uploaded_file in files:
        name = Path(str(getattr(uploaded_file, "name", ""))).name
        if not name or name in {".", ".."}:
            raise UploadValidationError("A file has an invalid name.")
        extension = Path(name).suffix.lower()
        if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
            raise UploadValidationError(
                f"Unsupported file type for {name}. Supported types: {supported}."
            )
        size = getattr(uploaded_file, "size", None)
        if size is None:
            size = len(uploaded_file.getbuffer())
        size = int(size)
        if size > max_file_bytes:
            raise UploadValidationError(
                f"{name} is {size / 1024 / 1024:.1f} MB; the per-file limit is "
                f"{max_file_bytes / 1024 / 1024:.1f} MB."
            )
        total_bytes += size

    if total_bytes > max_batch_bytes:
        raise UploadValidationError(
            f"The selected files total {total_bytes / 1024 / 1024:.1f} MB; "
            f"the batch limit is {max_batch_bytes / 1024 / 1024:.1f} MB."
        )
    return files


def extract_upload_batch(
    uploaded_files: Iterable[Any],
    *,
    max_files: int,
    max_file_bytes: int,
    max_batch_bytes: int,
    ocr_backend: OCRBackend | None = None,
    ocr_language: str = "eng",
    min_native_page_chars: int = 24,
    progress: Callable[[str], None] | None = None,
) -> list[ExtractedDocument]:
    """Validate a whole batch, then extract each file in upload order."""
    files = validate_upload_batch(
        uploaded_files,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
        max_batch_bytes=max_batch_bytes,
    )
    extracted: list[ExtractedDocument] = []
    for index, uploaded_file in enumerate(files, start=1):
        name = Path(str(getattr(uploaded_file, "name", ""))).name
        size = int(getattr(uploaded_file, "size", 0))
        if progress:
            progress(
                f"Reading file {index} of {len(files)}: {name} "
                f"({size / 1024 / 1024:.1f} MB)"
            )
        document = extract_uploaded_document(
            uploaded_file,
            ocr_backend=ocr_backend,
            ocr_language=ocr_language,
            min_native_page_chars=min_native_page_chars,
            progress=progress,
        )
        extracted.append(document)
        if progress:
            progress(
                f"Finished {name}: {len(document.text):,} characters; "
                f"OCR pages: {document.ocr_page_count}."
            )
    return extracted


def extract_uploaded_document(
    uploaded_file: Any,
    *,
    ocr_backend: OCRBackend | None = None,
    ocr_language: str = "eng",
    min_native_page_chars: int = 24,
    progress: Callable[[str], None] | None = None,
) -> ExtractedDocument:
    """Extract a single uploaded file without persisting it to disk."""
    file_name = Path(str(getattr(uploaded_file, "name", ""))).name
    extension = Path(file_name).suffix.lower()
    try:
        if hasattr(uploaded_file, "getvalue"):
            raw = uploaded_file.getvalue()
        else:
            uploaded_file.seek(0)
            raw = uploaded_file.read()
    except Exception as exc:
        raise DocumentExtractionError(f"Could not read {file_name}.") from exc
    if not raw:
        raise DocumentExtractionError(f"{file_name} is empty.")
    if len(raw) != int(getattr(uploaded_file, "size", len(raw))):
        raise DocumentExtractionError(
            f"The uploaded size for {file_name} changed during extraction."
        )

    if extension == ".pdf":
        return _extract_pdf(
            file_name, raw, ocr_backend, ocr_language,
            min_native_page_chars, progress,
        )
    if extension == ".docx":
        text = _extract_docx(raw)
        return ExtractedDocument(file_name, text, len(raw), None)
    if extension in SUPPORTED_UPLOAD_EXTENSIONS:
        if ocr_backend is None:
            raise _ocr_unavailable(file_name)
        text = ocr_backend.image_to_text(raw, ocr_language).strip()
        if not text:
            raise DocumentExtractionError(
                f"OCR found no readable text in {file_name}. Check the image quality or OCR language."
            )
        return ExtractedDocument(file_name, text, len(raw), 1, 1)
    raise UploadValidationError(f"Unsupported file type for {file_name}.")


def _extract_pdf(
    file_name: str,
    raw: bytes,
    ocr_backend: OCRBackend | None,
    ocr_language: str,
    min_native_page_chars: int,
    progress: Callable[[str], None] | None,
) -> ExtractedDocument:
    try:
        reader = PdfReader(BytesIO(raw), strict=False)
        if reader.is_encrypted:
            raise DocumentExtractionError(
                f"{file_name} is password-protected and cannot be extracted."
            )
        output: list[str] = []
        ocr_pages = 0
        for page_number, page in enumerate(reader.pages, start=1):
            native_text = (page.extract_text() or "").strip()
            page_text = native_text
            has_page_images = _page_has_images(page)
            needs_ocr = (
                has_page_images
                and len(native_text) < min_native_page_chars
            )
            if needs_ocr:
                if ocr_backend is None:
                    raise _ocr_unavailable(
                        file_name,
                        detail=(
                            f"Page {page_number} contains little or no selectable text. "
                            "Scanned pages require the configured OCR engine."
                        ),
                    )
                page_image = ocr_backend.pdf_page_to_image(raw, page_number)
                page_text = ocr_backend.image_to_text(
                    page_image, ocr_language
                ).strip()
                ocr_pages += 1
            if page_text:
                output.append(f"PAGE {page_number}\n{page_text}")
            if progress:
                progress(f"{file_name}: processed page {page_number} of {len(reader.pages)}")
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError(
            f"Could not extract text from {file_name}: {exc}"
        ) from exc

    text = "\n\n".join(output).strip()
    if not text:
        raise DocumentExtractionError(
            f"No readable text was found in {file_name}."
        )
    return ExtractedDocument(file_name, text, len(raw), len(reader.pages), ocr_pages)


def _extract_docx(raw: bytes) -> str:
    try:
        document = WordDocument(BytesIO(raw))
    except Exception as exc:
        raise DocumentExtractionError(
            f"Could not open the Word document: {exc}"
        ) from exc

    content: list[str] = []
    for paragraph in document.paragraphs:
        value = paragraph.text.strip()
        if value:
            content.append(value)
    for table in document.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if values:
                content.append(" | ".join(values))
    text = "\n\n".join(content).strip()
    if not text:
        raise DocumentExtractionError(
            "The Word document contains no readable paragraph or table text."
        )
    return text


def _page_has_images(page: Any) -> bool:
    """Detect raster page content without assuming any document domain."""
    try:
        resources = page.get("/Resources")
        if resources is None:
            return False
        resources = resources.get_object()
        xobjects = resources.get("/XObject")
        if xobjects is None:
            return False
        for reference in xobjects.get_object().values():
            image = reference.get_object()
            if image.get("/Subtype") == "/Image":
                return True
    except Exception:
        return False
    return False


def _ocr_unavailable(file_name: str, detail: str | None = None) -> DocumentExtractionError:
    reason = f" {detail}" if detail else ""
    return DocumentExtractionError(
        f"{file_name} requires OCR.{reason} Install the configured OCR dependencies "
        "and make the OCR engine available on PATH, then retry."
    )


class TesseractOCRBackend:
    """Local OCR adapter; dependencies are loaded only when OCR is needed."""

    def __init__(self, tesseract_cmd: str | None = None):
        self.tesseract_cmd = tesseract_cmd

    def image_to_text(self, image_bytes: bytes, language: str = "eng") -> str:
        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            raise DocumentExtractionError(
                "OCR needs Pillow and pytesseract. Install the project requirements."
            ) from exc
        try:
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            with Image.open(BytesIO(image_bytes)) as image:
                return pytesseract.image_to_string(image, lang=language)
        except Exception as exc:
            raise DocumentExtractionError(
                f"The local OCR engine could not read the image: {exc}"
            ) from exc

    def pdf_page_to_image(self, pdf_bytes: bytes, page_number: int) -> bytes:
        try:
            import fitz
        except ImportError as exc:
            raise DocumentExtractionError(
                "Scanned PDF OCR needs PyMuPDF. Install the project requirements."
            ) from exc
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
                page = pdf.load_page(page_number - 1)
                pixmap = page.get_pixmap(dpi=180, alpha=False)
                return pixmap.tobytes("png")
        except Exception as exc:
            raise DocumentExtractionError(
                f"Could not render PDF page {page_number} for OCR: {exc}"
            ) from exc
