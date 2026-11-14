from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Document:
    """
    Represents a document processed by RARE.
    """

    file_name: str
    file_type: str
    source: str = "local"
    file_path: Optional[str] = None
    content: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def extension(self) -> str:
        """
        Return the document file extension.
        """

        return Path(self.file_name).suffix.lower()

    @property
    def content_length(self) -> int:
        """
        Return the number of characters in the document content.
        """

        return len(self.content)

    def has_content(self) -> bool:
        """
        Check whether the document contains usable text.
        """

        return bool(self.content and self.content.strip())