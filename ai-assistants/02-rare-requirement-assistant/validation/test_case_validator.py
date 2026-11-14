from typing import Any, Dict, List


REQUIRED_COLUMNS = [
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

PREVIOUS_COLUMNS = REQUIRED_COLUMNS[:-1]

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

ALLOWED_TYPES = {
    "Positive Case",
    "Negative Case",
    "E2E Case",
    "Edge Case",
}

ALLOWED_PRIORITIES = {
    "P0",
    "P1",
    "P2",
    "P3",
}

ALLOWED_SUITE_TYPES = {
    "Smoke",
    "Sanity",
    "Regression",
}

ALLOWED_AUTOMATION_TYPES = {
    "UI Automation",
    "API Automation",
    "Backend/DB",
}


class TestCaseValidationResult:
    """
    Represents the result of validating generated test cases.
    """

    def __init__(
        self,
        is_valid: bool,
        errors: List[str] | None = None,
        warnings: List[str] | None = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the validation result into a dictionary.
        """

        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class TestCaseValidator:
    """
    Performs structural and quality validation on
    LLM-generated test cases.
    """

    def validate(
        self,
        test_cases: List[Dict[str, Any]],
    ) -> TestCaseValidationResult:

        errors: List[str] = []
        warnings: List[str] = []

        if not test_cases:
            errors.append(
                "No test cases were generated."
            )

            return TestCaseValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
            )

        self._validate_required_columns(
            test_cases,
            errors,
        )

        self._validate_test_case_ids(
            test_cases,
            errors,
        )

        self._validate_required_values(
            test_cases,
            errors,
        )

        self._validate_allowed_values(
            test_cases,
            errors,
        )

        self._validate_test_steps_format(
            test_cases,
            errors,
            warnings,
        )

        self._detect_duplicate_cases(
            test_cases,
            warnings,
        )

        return TestCaseValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_required_columns(
        self,
        test_cases: List[Dict[str, Any]],
        errors: List[str],
    ) -> None:
        """
        Validate that all required columns are present.
        """

        if not test_cases:
            return

        first_case = test_cases[0]

        present_columns = list(first_case.keys())

        if any(
            all(column in present_columns for column in schema)
            for schema in (REQUIRED_COLUMNS, PREVIOUS_COLUMNS, LEGACY_COLUMNS)
        ):
            return

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in first_case
        ]

        errors.append(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    def _validate_test_case_ids(
        self,
        test_cases: List[Dict[str, Any]],
        errors: List[str],
    ) -> None:
        """
        Validate that every test case has a unique ID
        within the current generated response.

        IDs are intentionally not required to be globally
        sequential because RARE generates independently
        from multiple document chunks.
        """

        seen_ids = set()

        for index, test_case in enumerate(
            test_cases,
            start=1,
        ):
            test_case_id = str(
                test_case.get("Test Case ID", "")
            ).strip()

            if not test_case_id:
                errors.append(
                    f"Test case row {index} has no "
                    f"Test Case ID."
                )
                continue

            if test_case_id in seen_ids:
                errors.append(
                    f"Duplicate Test Case ID found: "
                    f"{test_case_id}"
                )

            seen_ids.add(test_case_id)

    def _validate_required_values(
        self,
        test_cases: List[Dict[str, Any]],
        errors: List[str],
    ) -> None:
        """
        Validate that required fields contain values.
        """

        required_fields = [
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

        for index, test_case in enumerate(
            test_cases,
            start=1,
        ):
            for field in required_fields:

                if field == "Pre Condition" and "Pre Condition" not in test_case:
                    continue
                if field == "Requirement Reference" and field not in test_case:
                    continue

                value = test_case.get(field)

                if field in {"Pre Condition", "Requirement Reference"} and str(value or "").strip().lower() == "none":
                    continue

                if value is None or not str(value).strip():
                    errors.append(
                        f"Row {index} "
                        f"({test_case.get('Test Case ID', 'UNKNOWN')}): "
                        f"'{field}' is empty."
                    )

    def _validate_allowed_values(
        self,
        test_cases: List[Dict[str, Any]],
        errors: List[str],
    ) -> None:
        """
        Validate controlled vocabulary fields.
        """

        for index, test_case in enumerate(
            test_cases,
            start=1,
        ):
            test_case_id = test_case.get(
                "Test Case ID",
                f"ROW-{index}",
            )

            test_type = str(
                test_case.get("Type", "")
            ).strip()

            if test_type not in ALLOWED_TYPES:
                errors.append(
                    f"{test_case_id}: Invalid Type "
                    f"'{test_type}'."
                )

            priority = str(
                test_case.get("Priority", "")
            ).strip()

            if priority not in ALLOWED_PRIORITIES:
                errors.append(
                    f"{test_case_id}: Invalid Priority "
                    f"'{priority}'."
                )

            suite_type = str(
                test_case.get("Suite Type", "")
            ).strip()

            if suite_type not in ALLOWED_SUITE_TYPES:
                errors.append(
                    f"{test_case_id}: Invalid Suite Type "
                    f"'{suite_type}'."
                )

            automation_type = str(
                test_case.get("Automation Type", "")
            ).strip()

            if automation_type not in ALLOWED_AUTOMATION_TYPES:
                errors.append(
                    f"{test_case_id}: Invalid Automation Type "
                    f"'{automation_type}'."
                )

    def _validate_test_steps_format(
        self,
        test_cases: List[Dict[str, Any]],
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """
        Validate formatting of generated test steps.
        """

        for index, test_case in enumerate(
            test_cases,
            start=1,
        ):
            test_case_id = test_case.get(
                "Test Case ID",
                f"ROW-{index}",
            )

            steps = str(
                test_case.get("Test Steps", "")
            ).strip()

            if not steps:
                continue

            if "\n" in steps:
                warnings.append(
                    f"{test_case_id}: Test Steps contain "
                    f"normal line breaks. Expected <br> "
                    f"between steps."
                )

            if "<br>" not in steps and "<br/>" not in steps:
                warnings.append(
                    f"{test_case_id}: Test Steps do not "
                    f"contain <br> separators."
                )

            if "\\<br>" in steps:
                errors.append(
                    f"{test_case_id}: Test Steps contain "
                    f"escaped '<br>' formatting."
                )

    def _detect_duplicate_cases(
        self,
        test_cases: List[Dict[str, Any]],
        warnings: List[str],
    ) -> None:
        """
        Detect duplicate scenario descriptions.
        """

        seen_scenarios = {}

        for test_case in test_cases:

            test_case_id = test_case.get(
                "Test Case ID",
                "UNKNOWN",
            )

            scenario = str(
                test_case.get("Scenario", "")
            ).strip().lower()

            if not scenario:
                continue

            if scenario in seen_scenarios:
                warnings.append(
                    f"{test_case_id}: Scenario appears "
                    f"duplicated with "
                    f"{seen_scenarios[scenario]}."
                )
            else:
                seen_scenarios[scenario] = test_case_id
