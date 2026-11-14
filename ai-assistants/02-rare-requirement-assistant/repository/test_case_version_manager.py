from typing import List

from models.test_case import TestCase
from repository.test_case_change_detector import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    REVIEW,
    TestCaseChange,
)
from repository.test_case_repository import (
    TestCaseRepository,
)


class TestCaseVersionManager:
    """
    Applies detected test-case changes to the repository
    while preserving Test Case ID and version history.

    Supported actions:

        KEEP
        MODIFY
        ADD
        RETIRE

    Rules:

        KEEP
            Existing test case remains unchanged.

        MODIFY
            Existing Test Case ID is preserved.
            A new version is created.

        ADD
            A new globally unique Test Case ID is assigned.
            Version starts at 1.

        RETIRE
            Existing Test Case ID is preserved.
            A new RETIRED version is created.

        REVIEW
            Existing test case remains unchanged.
            No repository version is created.
            Manual review is required.
    """

    def __init__(
        self,
        repository: TestCaseRepository | None = None,
    ):
        self.repository = (
            repository
            or TestCaseRepository()
        )

    def apply_changes(
        self,
        changes: List[TestCaseChange],
    ) -> List[TestCase]:
        """
        Apply detected changes to the repository.

        Returns:
            The latest repository version of every affected
            test case.
        """

        if not changes:
            return []

        affected_cases = []

        for change in changes:

            if change.action == KEEP:

                if change.existing_test_case:
                    affected_cases.append(
                        change.existing_test_case
                    )

            elif change.action == MODIFY:

                updated_case = (
                    self._apply_modify(
                        change
                    )
                )

                affected_cases.append(
                    updated_case
                )

            elif change.action == ADD:

                new_case = (
                    self._apply_add(
                        change
                    )
                )

                affected_cases.append(
                    new_case
                )

            elif change.action == RETIRE:

                retired_case = (
                    self._apply_retire(
                        change
                    )
                )

                affected_cases.append(
                    retired_case
                )

            elif change.action == REVIEW:

                # REVIEW is intentionally a safe no-op.
                # The change detector could not safely determine
                # whether the existing test case should be changed
                # or retired. Leave the repository unchanged.
                continue

            else:

                raise ValueError(
                    "Unsupported change action: "
                    f"{change.action}"
                )

        return affected_cases

    def _apply_modify(
        self,
        change: TestCaseChange,
    ) -> TestCase:
        """
        Create a new version of an existing test case
        while preserving its Test Case ID.
        """

        existing_case = (
            change.existing_test_case
        )

        new_case = change.new_test_case

        if existing_case is None:
            raise ValueError(
                "MODIFY action requires an "
                "existing test case."
            )

        if new_case is None:
            raise ValueError(
                "MODIFY action requires a "
                "new test case."
            )

        updated_case = TestCase(
            test_case_id=(
                existing_case.test_case_id
            ),
            module=new_case.module,
            scenario=new_case.scenario,
            test_steps=new_case.test_steps,
            expected_result=new_case.expected_result,
            priority=new_case.priority,
            test_type=new_case.test_type,
            suite_type=new_case.suite_type,
            automation_type=new_case.automation_type,
            pre_condition=new_case.pre_condition,
            requirement_reference=(
                new_case.requirement_reference
                or existing_case.requirement_reference
            ),
            version=(
                existing_case.version + 1
            ),
            status="ACTIVE",
            source_document=(
                new_case.source_document
                or existing_case.source_document
            ),
        )

        return self.repository.update(
            updated_case
        )

    def _apply_add(
        self,
        change: TestCaseChange,
    ) -> TestCase:
        """
        Add a genuinely new test case.

        A new globally unique Test Case ID is assigned.
        """

        new_case = change.new_test_case

        if new_case is None:
            raise ValueError(
                "ADD action requires a "
                "new test case."
            )

        new_test_case_id = (
            self._get_next_test_case_id()
        )

        added_case = TestCase(
            test_case_id=new_test_case_id,
            module=new_case.module,
            scenario=new_case.scenario,
            test_steps=new_case.test_steps,
            expected_result=new_case.expected_result,
            priority=new_case.priority,
            test_type=new_case.test_type,
            suite_type=new_case.suite_type,
            automation_type=new_case.automation_type,
            pre_condition=new_case.pre_condition,
            requirement_reference=(
                new_case.requirement_reference
            ),
            version=1,
            status="ACTIVE",
            source_document=(
                new_case.source_document
            ),
        )

        return self.repository.save(
            added_case
        )

    def _apply_retire(
        self,
        change: TestCaseChange,
    ) -> TestCase:
        """
        Create a new RETIRED version of an existing
        test case while preserving its Test Case ID.
        """

        existing_case = (
            change.existing_test_case
        )

        if existing_case is None:
            raise ValueError(
                "RETIRE action requires an "
                "existing test case."
            )

        retired_case = (
            existing_case.retire()
        )

        return self.repository.update(
            retired_case
        )

    def _get_next_test_case_id(
        self,
    ) -> str:
        """
        Find the next available global Test Case ID.

        Existing IDs are scanned so that IDs are never
        accidentally reused.
        """

        test_cases = (
            self.repository.get_all()
        )

        highest_number = 0

        for test_case in test_cases:

            test_case_id = (
                test_case.test_case_id
            )

            if not test_case_id.startswith(
                "TC"
            ):
                continue

            numeric_part = (
                test_case_id[2:]
            )

            if not numeric_part.isdigit():
                continue

            number = int(
                numeric_part
            )

            highest_number = max(
                highest_number,
                number,
            )

        return (
            f"TC{highest_number + 1:03d}"
        )