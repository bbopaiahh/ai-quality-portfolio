from pathlib import Path

from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.docx_parser import extract_text_from_docx


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


def extract_text(file_path: str | Path) -> str:
    """
    Extract text from a supported document.

    Supported formats:
        - PDF
        - DOCX

    Args:
        file_path: Path to the document.

    Returns:
        Extracted document text.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Document not found: {file_path}"
        )

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document type: {extension}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension == ".docx":
        return extract_text_from_docx(file_path)

    # This should never be reached because of the validation above.
    raise ValueError(
        f"No parser available for document type: {extension}"
    )