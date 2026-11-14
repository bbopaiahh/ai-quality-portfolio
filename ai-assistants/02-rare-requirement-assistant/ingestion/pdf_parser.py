from pathlib import Path

from PyPDF2 import PdfReader


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract text from all pages of a PDF document.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text as a single string.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, received: {file_path.suffix}")

    reader = PdfReader(str(file_path))

    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""

            if page_text.strip():
                extracted_pages.append(page_text)

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract text from PDF page {page_number}"
            ) from exc

    return "\n\n".join(extracted_pages)