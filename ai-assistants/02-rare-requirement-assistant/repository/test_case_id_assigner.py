from typing import List

from models.test_case import TestCase


class TestCaseIdAssigner:
    """
    Assigns globally unique Test Case IDs after test cases
    from multiple document chunks have been combined.

    Test Case IDs generated independently by the LLM may
    restart from TC001 for each chunk. This component
    replaces those temporary IDs with globally unique IDs.

    Example:

        Chunk 1:
            TC001
            TC002
            TC003

        Chunk 2:
            TC001
            TC002

        Becomes:

            TC001
            TC002
            TC003
            TC004
            TC005
    """

    def assign(
        self,
        test_cases: List[TestCase],
        start_number: int = 1,
    ) -> List[TestCase]:
        """
        Assign globally unique sequential IDs.

        Args:
            test_cases:
                Test cases generated from one or more chunks.

            start_number:
                Starting numeric value for the first
                generated Test Case ID.

        Returns:
            Test cases with globally unique IDs.
        """

        if start_number < 1:
            raise ValueError(
                "start_number must be greater than or equal to 1."
            )

        if not test_cases:
            return []

        updated_test_cases = []

        current_number = start_number

        for test_case in test_cases:

            new_test_case = self._copy_with_new_id(
                test_case,
                f"TC{current_number:03d}",
            )

            updated_test_cases.append(
                new_test_case
            )

            current_number += 1

        return updated_test_cases

    def assign_from_chunks(
        self,
        test_case_chunks: List[List[TestCase]],
        start_number: int = 1,
    ) -> List[TestCase]:
        """
        Flatten test cases generated from multiple chunks
        and assign globally unique IDs.

        Example:

            [
                [TC001, TC002],
                [TC001, TC002, TC003],
            ]

        becomes:

            [TC001, TC002, TC003, TC004, TC005]
        """

        all_test_cases = []

        for chunk in test_case_chunks:
            if chunk:
                all_test_cases.extend(
                    chunk
                )

        return self.assign(
            all_test_cases,
            start_number=start_number,
        )

    @staticmethod
    def _copy_with_new_id(
        test_case: TestCase,
        new_test_case_id: str,
    ) -> TestCase:
        """
        Create a new TestCase object with the same
        content but a new globally unique Test Case ID.

        The original TestCase object is not modified.
        """

        return TestCase(
            test_case_id=new_test_case_id,
            module=test_case.module,
            scenario=test_case.scenario,
            test_steps=test_case.test_steps,
            expected_result=test_case.expected_result,
            priority=test_case.priority,
            test_type=test_case.test_type,
            suite_type=test_case.suite_type,
            automation_type=test_case.automation_type,
            requirement_reference=(
                test_case.requirement_reference
            ),
            version=test_case.version,
            status=test_case.status,
            source_document=test_case.source_document,
            created_at=test_case.created_at,
            updated_at=test_case.updated_at,
        )