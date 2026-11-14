from typing import List, Optional

from models.requirement import Requirement


class RequirementExtractor:
    """
    Extracts structured Requirement objects from BRD content.

    The extractor uses deterministic rule-based extraction so that
    requirement identification remains predictable and repeatable.

    A module heading remains associated with subsequent requirement
    statements until another module heading is encountered.
    """

    REQUIREMENT_KEYWORDS = (
        "must",
        "should",
        "shall",
        "required",
        "mandatory",
        "cannot",
        "cannot be",
        "needs to",
        "need to",
        "only if",
        "exactly",
        "greater than",
        "less than",
        "within",
        "before",
        "after",
        "reject",
        "rejected",
        "prevent",
        "prevents",
        "allow",
        "allows",
        "transition",
        "encrypted",
        "retry",
    )

    PRIORITY_KEYWORDS = {
        "P0": (
            "critical",
            "must",
            "security",
            "authentication",
            "encryption",
        ),
        "P1": (
            "required",
            "validation",
            "reject",
            "prevent",
            "mandatory",
            "transition",
            "retry",
        ),
        "P2": (
            "should",
            "edge",
            "boundary",
            "performance",
        ),
    }

    def __init__(self):
        self._next_requirement_number = 1

    def extract(
        self,
        content: str,
        source_document: str = "Unknown",
    ) -> List[Requirement]:
        """
        Extract requirements from supplied BRD content.

        Module context is preserved across blank lines.
        """

        if not content or not content.strip():
            return []

        self._next_requirement_number = 1

        normalized = (
            content
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )

        lines = normalized.splitlines()

        requirements: List[Requirement] = []
        current_module = "General"

        for line in lines:
            cleaned = self._clean_line(line)

            if not cleaned:
                continue

            module = self._extract_module_from_line(cleaned)

            if module:
                current_module = module
                continue

            if not self._looks_like_requirement(cleaned):
                continue

            requirement = self._create_requirement(
                requirement_text=cleaned,
                module=current_module,
                source_document=source_document,
            )

            requirements.append(requirement)

        return requirements

    def _create_requirement(
        self,
        requirement_text: str,
        module: str,
        source_document: str,
    ) -> Requirement:
        """
        Create a Requirement object with the next generated ID.
        """

        requirement_id = self._generate_requirement_id()

        requirement_type = self._determine_requirement_type(
            requirement_text
        )

        priority = self._determine_priority(
            requirement_text
        )

        return Requirement(
            requirement_id=requirement_id,
            module=module,
            requirement=requirement_text,
            requirement_type=requirement_type,
            priority=priority,
            source_document=source_document,
            source_reference=module,
        )

    def _extract_module_from_line(
        self,
        line: str,
    ) -> Optional[str]:
        """
        Extract a module name from an explicit module heading.
        """

        lower_line = line.lower()

        if lower_line.startswith("module:"):
            module = line.split(":", 1)[1].strip()

            return module if module else None

        if lower_line.startswith("module -"):
            module = line.split("-", 1)[1].strip()

            return module if module else None

        if lower_line.startswith("module "):
            module = line[7:].strip()

            return module if module else None

        return None

    def _determine_requirement_type(
        self,
        requirement_text: str,
    ) -> str:
        """
        Classify a requirement using deterministic keywords.
        """

        text = requirement_text.lower()

        if any(
            keyword in text
            for keyword in (
                "performance",
                "response time",
                "seconds",
                "records",
            )
        ):
            return "Performance"

        if any(
            keyword in text
            for keyword in (
                "encrypt",
                "security",
                "authentication",
                "authorization",
                "token",
            )
        ):
            return "Security"

        if any(
            keyword in text
            for keyword in (
                "api",
                "endpoint",
                "http",
                "request",
                "response",
            )
        ):
            return "API"

        if any(
            keyword in text
            for keyword in (
                "business rule",
                "must",
                "shall",
                "required",
                "mandatory",
                "cannot",
                "exactly",
                "greater than",
                "less than",
            )
        ):
            return "Business Rule"

        return "Functional"

    def _determine_priority(
        self,
        requirement_text: str,
    ) -> str:
        """
        Determine priority from requirement wording.
        """

        text = requirement_text.lower()

        for priority in ("P0", "P1", "P2"):
            keywords = self.PRIORITY_KEYWORDS[priority]

            if any(
                keyword in text
                for keyword in keywords
            ):
                return priority

        return "P2"

    def _looks_like_requirement(
        self,
        line: str,
    ) -> bool:
        """
        Determine whether a line represents a requirement.
        """

        text = line.lower()

        if text.startswith(
            (
                "requirement:",
                "requirement -",
                "business rule:",
                "business rule -",
                "expected result:",
            )
        ):
            return True

        return any(
            keyword in text
            for keyword in self.REQUIREMENT_KEYWORDS
        )

    @staticmethod
    def _clean_line(
        line: str,
    ) -> str:
        """
        Remove common Markdown/list formatting.
        """

        cleaned = line.strip()

        prefixes = (
            "- ",
            "* ",
            "• ",
        )

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        while cleaned.startswith("#"):
            cleaned = cleaned[1:].strip()

        return cleaned

    def _generate_requirement_id(self) -> str:
        """
        Generate the next requirement ID.
        """

        requirement_id = (
            f"REQ{self._next_requirement_number:03d}"
        )

        self._next_requirement_number += 1

        return requirement_id