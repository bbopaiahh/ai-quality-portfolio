from models.test_case import TestCase
from repository.test_case_id_assigner import (
    TestCaseIdAssigner,
)


def create_test_case(
    test_case_id: str,
    scenario: str,
) -> TestCase:

    return TestCase(
        test_case_id=test_case_id,
        module="Lead Management",
        scenario=scenario,
        test_steps=(
            "1. Open Lead page<br>"
            "2. Enter test data<br>"
            "3. Save lead"
        ),
        expected_result="Lead is processed correctly.",
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="UI Automation",
        source_document="BRD.docx",
    )


def main():

    print("1. Creating test cases from Chunk 1...")

    chunk_1 = [
        create_test_case(
            "TC001",
            "Create valid lead",
        ),
        create_test_case(
            "TC002",
            "Validate mandatory fields",
        ),
        create_test_case(
            "TC003",
            "Validate mobile number",
        ),
    ]

    print("Chunk 1:")
    for test_case in chunk_1:
        print(
            test_case.test_case_id,
            "|",
            test_case.scenario,
        )

    print("\n2. Creating test cases from Chunk 2...")

    chunk_2 = [
        create_test_case(
            "TC001",
            "Check duplicate lead",
        ),
        create_test_case(
            "TC002",
            "Validate CIBIL",
        ),
        create_test_case(
            "TC003",
            "Validate DTI",
        ),
    ]

    print("Chunk 2:")
    for test_case in chunk_2:
        print(
            test_case.test_case_id,
            "|",
            test_case.scenario,
        )

    print("\n3. Assigning global IDs...")

    assigner = TestCaseIdAssigner()

    result = assigner.assign_from_chunks(
        [
            chunk_1,
            chunk_2,
        ]
    )

    print("\nFinal globally assigned IDs:")

    for test_case in result:
        print(
            test_case.test_case_id,
            "|",
            test_case.scenario,
        )

    print("\n4. Verifying uniqueness...")

    ids = [
        test_case.test_case_id
        for test_case in result
    ]

    if len(ids) != len(set(ids)):
        raise AssertionError(
            "Duplicate Test Case IDs detected."
        )

    print(
        "Unique IDs:",
        len(set(ids)),
    )

    print("\n5. Verifying expected sequence...")

    expected_ids = [
        "TC001",
        "TC002",
        "TC003",
        "TC004",
        "TC005",
        "TC006",
    ]

    if ids != expected_ids:
        raise AssertionError(
            f"Unexpected ID sequence: {ids}"
        )

    print(
        "Expected sequence verified."
    )

    print(
        "\nGlobal Test Case ID assignment "
        "test completed successfully."
    )


if __name__ == "__main__":
    main()