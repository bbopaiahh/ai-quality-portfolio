import re
import unicodedata
from typing import Any, Callable, Dict, List

from generation.llm_client import LLMClient
from generation.prompts import load_test_generation_prompt
from validation.test_case_validator import (
    ALLOWED_AUTOMATION_TYPES,
    ALLOWED_PRIORITIES,
    ALLOWED_SUITE_TYPES,
    ALLOWED_TYPES,
    LEGACY_COLUMNS,
    PREVIOUS_COLUMNS,
    REQUIRED_COLUMNS as VALIDATOR_REQUIRED_COLUMNS,
    TestCaseValidator,
)


class TestGenerator:
    """
    Generates a Master Test Suite using document chunks
    and the configured LLM.

    The generated Markdown table is parsed and validated
    before it is returned to the application.
    """

    REQUIRED_COLUMNS = VALIDATOR_REQUIRED_COLUMNS

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()
        self.base_prompt = load_test_generation_prompt()
        self.validator = TestCaseValidator()

    def generate_from_chunk(
        self,
        chunk: str,
        *,
        requirement_catalog: list[Any] | None = None,
    ) -> str:
        """
        Generate and validate test cases from a single document chunk.

        Args:
            chunk: A chunk of extracted document text.

        Returns:
            Validated generated test-suite Markdown.
        """

        if not chunk or not chunk.strip():
            raise ValueError("Document chunk cannot be empty.")

        applicable_catalog = self._requirements_present_in_chunk(
            requirement_catalog,
            chunk,
        )
        prompt = self._build_prompt(chunk, applicable_catalog)

        result = self.llm_client.generate(prompt)

        if not result or not result.strip():
            raise RuntimeError(
                "LLM returned an empty test-generation result."
            )

        test_cases = self._parse_markdown_table(result)
        self._normalize_categories(test_cases)
        self._normalize_requirement_references(test_cases, applicable_catalog)
        validation_result = (
            self.validator.validate(test_cases)
            if test_cases
            else None
        )

        if not test_cases or not validation_result.is_valid:
            issue = (
                "No supported test-case table was found in the response."
                if not test_cases
                else "The response table failed validation: "
                + "; ".join(validation_result.errors)
            )
            repaired_result = self.llm_client.generate(
                self._build_format_repair_prompt(
                    chunk=chunk,
                    original_response=result,
                    issue=issue,
                    requirement_catalog=applicable_catalog,
                )
            )
            test_cases = self._parse_markdown_table(repaired_result)
            self._normalize_categories(test_cases)
            self._normalize_requirement_references(test_cases, applicable_catalog)
            if not test_cases:
                raise RuntimeError(
                    "The initial LLM response and one format-correction "
                    "attempt did not produce a supported test-case table."
                )

            validation_result = self.validator.validate(test_cases)
            if not validation_result.is_valid:
                error_message = "; ".join(validation_result.errors)
                raise RuntimeError(
                    "Generated test cases failed validation after one "
                    f"format-correction attempt: {error_message}"
                )

        # Return only validated rows in the canonical RARE table. The raw
        # model response can contain unrelated Markdown tables or malformed
        # rows after the valid table; forwarding that text makes the app's
        # repository parser treat those rows as test cases.
        return self._render_markdown_table(test_cases)

    def generate_from_chunks(
        self,
        chunks: List[str],
        *,
        progress: Callable[[int, int, str], None] | None = None,
        requirement_catalog: list[Any] | None = None,
    ) -> List[str]:
        """
        Generate and validate test cases independently
        for each document chunk.

        Args:
            chunks: List of document text chunks.
            progress: Optional callback receiving (index, total, state), where
                state is "started", "completed", or "failed". "started" means
                the configured provider call is in progress; the current
                synchronous client does not expose token-level progress.

        Returns:
            List containing validated generated output
            for each chunk.
        """

        if not chunks:
            return []

        generated_results = []

        for index, chunk in enumerate(chunks, start=1):
            if not chunk or not chunk.strip():
                continue

            try:
                if progress:
                    progress(index, len(chunks), "started")
                result = self.generate_from_chunk(
                    chunk,
                    requirement_catalog=requirement_catalog,
                )

                if result.strip():
                    generated_results.append(result)

            except Exception as exc:
                if progress:
                    progress(index, len(chunks), "failed")
                raise RuntimeError(
                    f"Test generation failed for chunk {index}."
                ) from exc

            if progress:
                progress(index, len(chunks), "completed")

        return generated_results

    def _build_prompt(
        self,
        chunk: str,
        requirement_catalog: list[Any] | None = None,
    ) -> str:
        """
        Combine the existing RARE prompt with the document chunk.
        """

        catalog_text = ""
        if requirement_catalog:
            catalog_rows = []
            for item in requirement_catalog:
                if isinstance(item, dict):
                    requirement_id = item.get("requirement_id", "")
                    requirement_text = item.get("requirement", "")
                else:
                    requirement_id = getattr(item, "requirement_id", "")
                    requirement_text = getattr(item, "requirement", "")
                if requirement_id and requirement_text:
                    catalog_rows.append(
                        f"{requirement_id}: {requirement_text}"
                    )
            if catalog_rows:
                catalog_text = (
                    "\n\n============================================================\n"
                    "RARE REQUIREMENT CATALOG — use these IDs for Requirement Reference\n"
                    "============================================================\n"
                    + "\n".join(catalog_rows)
                    + "\n\nUse only IDs shown above. Assign a reference only when the test "
                    "directly verifies that requirement; otherwise write None."
                )
        return f"""
{self.base_prompt}
{catalog_text}

============================================================
DOCUMENT CONTENT
============================================================

{chunk}

============================================================
END DOCUMENT CONTENT
============================================================
""".strip()

    def _build_format_repair_prompt(
        self,
        *,
        chunk: str,
        original_response: str,
        issue: str,
        requirement_catalog: list[Any] | None = None,
    ) -> str:
        """Ask the configured provider once to repair an unusable response."""
        response_excerpt = original_response[:20000]
        catalog_prompt = self._build_prompt(chunk, requirement_catalog)
        return f"""
The previous response could not be used: {issue}

Return ONLY one Markdown table using EXACTLY these columns in this order:
| Test Case ID | Module | Scenario | Pre Condition | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type | Requirement Reference |

Include one separator row and complete rows with all eleven columns. Do not add
headings, explanations, code fences, or any other tables. Preserve valid test
case meaning from the previous response. If it contains no usable test cases,
generate grounded cases from the requirement text below. Do not invent behavior;
use the clarification wording from the base instructions when the requirement
does not specify an expected outcome. If no precondition is stated, use None.
Escape any literal pipe inside a cell as \\|.
For Requirement Reference, use only an ID from the requirement catalog in the
generation prompt. Use None if no direct requirement link is supported.

Use only these exact category values:
- Priority: P0, P1, P2, P3 (Critical/Highest=P0, High=P1, Medium=P2, Low=P3)
- Type: Positive Case, Negative Case, E2E Case, Edge Case
- Suite Type: Smoke, Sanity, Regression. Performance is not a Suite Type;
  use Regression unless the case clearly belongs to Smoke or Sanity.
- Automation Type: UI Automation, API Automation, Backend/DB. Do not use the
  generic value Automated; choose a verification surface supported by the steps.

Functional and Non-Functional describe requirement categories, not test-case
Types. Classify each case from its scenario and expected behavior.

GENERATION PROMPT AND REQUIREMENT CATALOG:
{catalog_prompt}

PREVIOUS RESPONSE TO REPAIR:
{response_excerpt}
""".strip()

    def _parse_markdown_table(
        self,
        markdown: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse the first Markdown table found in the LLM response.

        The parser expects the current RARE test-case columns.
        """

        lines = [
            line.strip()
            for line in markdown.splitlines()
            if line.strip()
        ]

        header_index = None

        for index, line in enumerate(lines):
            if (
                line.startswith("|")
                and "Test Case ID" in line
                and "Scenario" in line
                and "Expected Result" in line
            ):
                header_index = index
                break

        if header_index is None:
            return []

        header_line = lines[header_index]

        headers = self._split_markdown_row(header_line)

        if headers not in (
            self.REQUIRED_COLUMNS,
            PREVIOUS_COLUMNS,
            LEGACY_COLUMNS,
        ):
            return []

        data_rows = []

        for line in lines[header_index + 2:]:
            if not line.startswith("|"):
                break

            values = self._split_markdown_row(line)

            if len(values) != len(headers):
                continue

            data_rows.append(
                dict(zip(headers, values))
            )

        return data_rows

    @staticmethod
    def _split_markdown_row(line: str) -> List[str]:
        """
        Split a Markdown table row while removing
        the surrounding pipe characters.
        """

        line = line.strip()

        if line.startswith("|"):
            line = line[1:]

        if line.endswith("|"):
            line = line[:-1]

        return [
            value.replace(r"\|", "|").strip()
            for value in re.split(r"(?<!\\)\|", line)
        ]

    @classmethod
    def _render_markdown_table(
        cls,
        test_cases: List[Dict[str, Any]],
    ) -> str:
        """
        Serialize only validated records using the canonical output schema.
        """
        headers = cls.REQUIRED_COLUMNS
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for test_case in test_cases:
            values = []
            for header in headers:
                default = (
                    "None"
                    if header in {"Pre Condition", "Requirement Reference"}
                    else ""
                )
                value = str(test_case.get(header, default) or default)
                value = value.replace("\\<br>", "<br>")
                value = value.replace("\r\n", "<br>").replace("\n", "<br>")
                values.append(value.replace("|", r"\|"))
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)

    @staticmethod
    def _normalize_requirement_references(
        test_cases: List[Dict[str, Any]],
        requirement_catalog: list[Any] | None,
    ) -> None:
        allowed_ids = set()
        for item in requirement_catalog or []:
            if isinstance(item, dict):
                requirement_id = item.get("requirement_id")
            else:
                requirement_id = getattr(item, "requirement_id", None)
            if requirement_id:
                allowed_ids.add(str(requirement_id).strip())

        for case in test_cases:
            raw_reference = str(case.get("Requirement Reference", "") or "")
            references = [
                token.strip()
                for token in re.split(r"[,;\n]+", raw_reference)
                if token.strip()
            ]
            valid_references = list(dict.fromkeys(
                reference for reference in references
                if reference in allowed_ids
            ))
            case["Requirement Reference"] = (
                ", ".join(valid_references) if valid_references else "None"
            )

    @staticmethod
    def _requirements_present_in_chunk(
        requirement_catalog: list[Any] | None,
        chunk: str,
    ) -> list[Any]:
        """Limit reference choices to requirements quoted in this source segment."""
        normalized_chunk = " ".join(
            unicodedata.normalize("NFKC", chunk).casefold().split()
        )
        applicable = []
        for item in requirement_catalog or []:
            if isinstance(item, dict):
                requirement_text = item.get("requirement", "")
            else:
                requirement_text = getattr(item, "requirement", "")
            normalized_requirement = " ".join(
                unicodedata.normalize(
                    "NFKC", str(requirement_text or "")
                ).casefold().split()
            )
            if normalized_requirement and normalized_requirement in normalized_chunk:
                applicable.append(item)
        return applicable

    @staticmethod
    def _normalize_categories(
        test_cases: List[Dict[str, Any]],
    ) -> None:
        """Map common generic model labels to the fixed, domain-neutral enums."""
        priority_aliases = {
            "critical": "P0", "highest": "P0", "high": "P1",
            "medium": "P2", "moderate": "P2", "low": "P3",
        }
        suite_aliases = {
            "smoke test": "Smoke", "sanity check": "Sanity",
            "performance": "Regression", "functional": "Regression",
        }
        type_aliases = {
            "positive": "Positive Case", "positive test": "Positive Case",
            "negative": "Negative Case", "negative test": "Negative Case",
            "e2e": "E2E Case", "end to end": "E2E Case",
            "edge": "Edge Case", "boundary": "Edge Case",
        }

        for case in test_cases:
            case["Priority"] = TestGenerator._normalize_enum(
                case.get("Priority"), ALLOWED_PRIORITIES, priority_aliases
            )
            case["Suite Type"] = TestGenerator._normalize_enum(
                case.get("Suite Type"), ALLOWED_SUITE_TYPES, suite_aliases
            )

            raw_type = TestGenerator._normalize_label(case.get("Type", ""))
            case_type = TestGenerator._normalize_enum(
                raw_type, ALLOWED_TYPES, type_aliases
            )
            if case_type not in ALLOWED_TYPES and raw_type.casefold() in {
                "functional", "non-functional", "non functional"
            }:
                case_type = TestGenerator._infer_test_type(case)
            case["Type"] = case_type

            raw_automation = TestGenerator._normalize_label(
                case.get("Automation Type", "")
            )
            if raw_automation.casefold() in {
                "automated", "automation", "automated test"
            }:
                description = " ".join(
                    str(case.get(field, ""))
                    for field in (
                        "Module", "Scenario", "Pre Condition",
                        "Test Steps", "Expected Result",
                    )
                ).casefold()
                if re.search(r"\b(api|http|rest|endpoint)\b", description):
                    raw_automation = "API Automation"
                elif re.search(r"\b(database|backend|sql|table|persist|audit log)\b", description):
                    raw_automation = "Backend/DB"
                else:
                    raw_automation = "UI Automation"
            case["Automation Type"] = TestGenerator._normalize_enum(
                raw_automation,
                ALLOWED_AUTOMATION_TYPES,
                {
                    "ui": "UI Automation", "api": "API Automation",
                    "backend": "Backend/DB", "database": "Backend/DB",
                },
            )

    @staticmethod
    def _normalize_enum(value, allowed_values, aliases):
        normalized = TestGenerator._normalize_label(value)
        for allowed in allowed_values:
            if normalized.casefold() == allowed.casefold():
                return allowed
        return aliases.get(normalized.casefold(), normalized)

    @staticmethod
    def _normalize_label(value) -> str:
        normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
        return re.sub(r"[\u2010-\u2015\u2212]", "-", normalized)

    @staticmethod
    def _infer_test_type(case: Dict[str, Any]) -> str:
        description = " ".join(
            str(case.get(field, ""))
            for field in ("Scenario", "Test Steps", "Expected Result")
        ).casefold()
        if re.search(r"\b(end.to.end|end to end|entire workflow|complete journey)\b", description):
            return "E2E Case"
        if re.search(r"\b(exactly|boundary|threshold|edge case|limit)\b", description):
            return "Edge Case"
        if re.search(r"\b(invalid|missing|without|reject|rejected|failure|fails|does not|not transition|not triggered)\b", description):
            return "Negative Case"
        return "Positive Case"
