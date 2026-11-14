from models.test_case import TestCase
from repository.test_case_change_detector import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    TestCaseChangeDetector,
)


def create_test_case(
    test_case_id: str,
    module: str,
    scenario: str,
    test_steps: str,
    expected_result: str,
) -> TestCase:

    return TestCase(
        test_case_id=test_case_id,
        module=module,
        scenario=scenario,
        test_steps=test_steps,
        expected_result=expected_result,
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="UI Automation",
        source_document="BRD.docx",
    )


def main():

    detector = TestCaseChangeDetector()

    # ========================================================
    # Existing repository
    # ========================================================

    existing_cases = [

        create_test_case(
            "TC001",
            "Lead Creation",
            "Create valid lead",
            "1. Open Lead page<br>"
            "2. Enter valid data<br>"
            "3. Save lead",
            "Lead is created successfully.",
        ),

        create_test_case(
            "TC002",
            "Lead Creation",
            "Validate mobile number",
            "1. Open Lead page<br>"
            "2. Enter mobile number<br>"
            "3. Save lead",
            "Mobile number is validated.",
        ),

        create_test_case(
            "TC003",
            "Eligibility",
            "Validate CIBIL",
            "1. Enter CIBIL score<br>"
            "2. Submit eligibility",
            "CIBIL validation is performed.",
        ),

        create_test_case(
            "TC004",
            "Underwriting",
            "Validate DTI",
            "1. Enter DTI<br>"
            "2. Approve application",
            "DTI validation is performed.",
        ),
    ]

    print("1. Existing repository:")

    for test_case in existing_cases:

        print(
            f"{test_case.test_case_id} | "
            f"{test_case.module} | "
            f"{test_case.scenario}"
        )

    # ========================================================
    # Newly generated suite
    # ========================================================

    new_cases = [

        # KEEP
        create_test_case(
            "TC001",
            "Lead Creation",
            "Create valid lead",
            "1. Open Lead page<br>"
            "2. Enter valid data<br>"
            "3. Save lead",
            "Lead is created successfully.",
        ),

        # MODIFY
        create_test_case(
            "TC001",
            "Lead Creation",
            "Validate mobile number",
            "1. Open Lead page<br>"
            "2. Enter 10 digit mobile number<br>"
            "3. Save lead",
            "System validates the mobile number "
            "and displays the result.",
        ),

        # KEEP
        create_test_case(
            "TC001",
            "Eligibility",
            "Validate CIBIL",
            "1. Enter CIBIL score<br>"
            "2. Submit eligibility",
            "CIBIL validation is performed.",
        ),

        # ADD
        create_test_case(
            "TC001",
            "Document Checklist",
            "Validate mandatory documents",
            "1. Upload mandatory documents<br>"
            "2. Submit documents",
            "Mandatory documents are validated.",
        ),
    ]

    print("\n2. Newly generated suite:")

    for test_case in new_cases:

        print(
            f"{test_case.test_case_id} | "
            f"{test_case.module} | "
            f"{test_case.scenario}"
        )

    # ========================================================
    # Detect changes
    # ========================================================

    print("\n3. Detecting changes...")

    changes = detector.detect(
        new_cases,
        existing_cases,
    )

    for change in changes:

        print(
            f"{change.action} | "
            f"{change.test_case_id or 'NEW'} | "
            f"{change.reason}"
        )

    # ========================================================
    # Validate results
    # ========================================================

    print("\n4. Validating change detection...")

    summary = detector.summarize(
        changes
    )

    print(
        f"KEEP: {summary[KEEP]}"
    )

    print(
        f"MODIFY: {summary[MODIFY]}"
    )

    print(
        f"ADD: {summary[ADD]}"
    )

    print(
        f"RETIRE: {summary[RETIRE]}"
    )

    # The expected result is:
    #
    # TC001 → KEEP
    # TC002 → MODIFY
    # TC003 → KEEP
    # New case → ADD
    # TC004 → RETIRE

    expected = {
        KEEP: 2,
        MODIFY: 1,
        ADD: 1,
        RETIRE: 1,
    }

    for action, expected_count in expected.items():

        actual_count = summary[action]

        if actual_count != expected_count:

            raise AssertionError(
                f"Expected {expected_count} "
                f"{action} cases but found "
                f"{actual_count}."
            )

    print(
        "\nChange detection test "
        "completed successfully."
    )


if __name__ == "__main__":
    main()