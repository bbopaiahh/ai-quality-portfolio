import re
from typing import List

from models.test_case import TestCase


EXPECTED_COLUMNS = [
    "Test Case ID",
    "Module",
    "Scenario",
    "Pre Condition",
    "Test Steps",
    "Expected Result",
    "Priority",
    "Type",
    "Suite Type",
    "Automation Type",
    "Requirement Reference",
]

PREVIOUS_COLUMNS = EXPECTED_COLUMNS[:-1]

LEGACY_COLUMNS = [
    "Test Case ID",
    "Module",
    "Scenario",
    "Test Steps",
    "Expected Result",
    "Priority",
    "Type",
    "Suite Type",
    "Automation Type",
]


class TestCaseParser:
    """
    Converts the generated Markdown test-suite table
    into TestCase model objects.
    """

    def parse(
        self,
        markdown_table: str,
        source_document: str | None = None,
    ) -> List[TestCase]:
        """
        Parse a Markdown table into TestCase objects.
        """

        if not markdown_table:
            return []

        lines = [
            line.strip()
            for line in markdown_table.splitlines()
            if line.strip()
        ]

        table_lines = [
            line
            for line in lines
            if line.startswith("|")
            and line.endswith("|")
        ]

        if len(table_lines) < 3:
            raise ValueError(
                "Generated output does not contain "
                "a valid Markdown test-case table."
            )

        headers = self._parse_row(
            table_lines[0]
        )

        self._validate_headers(headers)

        test_cases = []

        for line in table_lines[2:]:
            values = self._parse_row(line)

            if not values:
                continue

            if self._is_separator_row(values):
                continue

            if len(values) != len(headers):
                raise ValueError(
                    "Invalid test-case row. "
                    f"Expected {len(headers)} columns "
                    f"but found {len(values)}."
                )

            row = dict(
                zip(headers, values)
            )

            test_case = TestCase(
                test_case_id=row[
                    "Test Case ID"
                ].strip(),

                module=row[
                    "Module"
                ].strip(),

                scenario=row[
                    "Scenario"
                ].strip(),

                pre_condition=self._clean_html(
                    row.get("Pre Condition", "")
                ),

                test_steps=self._clean_html(
                    row["Test Steps"]
                ),

                expected_result=self._clean_html(
                    row["Expected Result"]
                ),

                priority=row[
                    "Priority"
                ].strip(),

                test_type=row[
                    "Type"
                ].strip(),

                suite_type=row[
                    "Suite Type"
                ].strip(),

                automation_type=row[
                    "Automation Type"
                ].strip(),

                requirement_reference=(
                    row.get("Requirement Reference", "").strip()
                    if row.get("Requirement Reference", "").strip().lower()
                    not in {"", "none"}
                    else None
                ),

                source_document=source_document,
            )

            test_cases.append(
                test_case
            )

        return test_cases

    def parse_multiple(
        self,
        generated_results: List[str],
        source_document: str | None = None,
    ) -> List[TestCase]:
        """
        Parse multiple generated chunks into a single
        list of TestCase objects.
        """

        all_test_cases = []

        for result in generated_results:
            parsed = self.parse(
                result,
                source_document=source_document,
            )

            all_test_cases.extend(
                parsed
            )

        self._validate_unique_ids(
            all_test_cases
        )

        return all_test_cases

    @staticmethod
    def _parse_row(
        line: str,
    ) -> List[str]:
        """
        Parse one Markdown table row.
        """

        content = line.strip()[1:-1]

        return [
            value.replace(r"\|", "|").strip()
            for value in re.split(r"(?<!\\)\|", content)
        ]

    @staticmethod
    def _validate_headers(
        headers: List[str],
    ) -> None:

        if headers not in (EXPECTED_COLUMNS, PREVIOUS_COLUMNS, LEGACY_COLUMNS):
            raise ValueError(
                "Generated table columns do not match "
                "the expected RARE test-case schema."
            )

    @staticmethod
    def _is_separator_row(
        values: List[str],
    ) -> bool:

        return all(
            re.fullmatch(
                r":?-+:?",
                value,
            )
            for value in values
        )

    @staticmethod
    def _clean_html(
        value: str,
    ) -> str:
        """
        Preserve the generated content while removing
        accidental escaped HTML syntax.

        The broader <br> formatting cleanup remains a
        separate final output-cleanup task.
        """

        return value.replace(
            "\\<br>",
            "<br>",
        )

    @staticmethod
    def _validate_unique_ids(
        test_cases: List[TestCase],
    ) -> None:

        seen = set()

        for test_case in test_cases:

            test_case_id = (
                test_case.test_case_id
            )

            if test_case_id in seen:
                raise ValueError(
                    "Duplicate Test Case ID found "
                    f"during parsing: {test_case_id}"
                )

            seen.add(
                test_case_id
            )
