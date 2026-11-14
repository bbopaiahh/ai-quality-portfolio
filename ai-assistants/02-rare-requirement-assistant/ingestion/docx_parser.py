from pathlib import Path

from docx import Document


def extract_text_from_docx(file_path: str | Path) -> str:
    """
    Extract text from paragraphs and tables in a DOCX document.

    Args:
        file_path: Path to the DOCX file.

    Returns:
        Extracted text as a single string.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"DOCX file not found: {file_path}")

    if file_path.suffix.lower() != ".docx":
        raise ValueError(
            f"Expected a DOCX file, received: {file_path.suffix}"
        )

    document = Document(str(file_path))

    extracted_content = []

    # ---------------------------------------------------------
    # Paragraphs
    # ---------------------------------------------------------

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            extracted_content.append(text)

    # ---------------------------------------------------------
    # Tables
    # ---------------------------------------------------------

    for table in document.tables:
        for row in table.rows:
            row_values = []

            for cell in row.cells:
                cell_text = cell.text.strip()

                if cell_text:
                    row_values.append(cell_text)

            if row_values:
                extracted_content.append(" | ".join(row_values))

    return "\n\n".join(extracted_content)