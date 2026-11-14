from models.test_case import TestCase
from repository.test_case_id_assigner import (
    TestCaseIdAssigner,
)
from repository.test_case_parser import (
    TestCaseParser,
)
from repository.test_case_repository import (
    TestCaseRepository,
)
from repository.test_case_service import (
    TestCaseService,
)


GENERATED_CHUNK_1 = """
| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|
| TC001 | Lead Creation | Create valid lead | 1. Open Lead page<br>2. Enter valid data<br>3. Save lead | Lead is created successfully. | P1 | Positive Case | Smoke | UI Automation |
| TC002 | Lead Creation | Validate mandatory fields | 1. Open Lead page<br>2. Leave mandatory field empty<br>3. Save lead | Appropriate validation is displayed. | P1 | Negative Case | Smoke | UI Automation |
| TC003 | Lead Validation | Validate mobile number | 1. Open Lead page<br>2. Enter mobile number<br>3. Save lead | Mobile number is validated. | P2 | Positive Case | Regression | UI Automation |
"""


GENERATED_CHUNK_2 = """
| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|
| TC001 | Lead Validation | Check duplicate lead | 1. Enter existing lead data<br>2. Save lead | Duplicate lead handling follows the requirement. | P1 | Negative Case | Regression | UI Automation |
| TC002 | Eligibility | Validate CIBIL | 1. Enter applicant details<br>2. Submit eligibility request | CIBIL validation is performed. | P1 | Positive Case | Smoke | API Automation |
| TC003 | Eligibility | Validate DTI | 1. Enter applicant financial data<br>2. Submit eligibility request | DTI validation is performed. | P1 | Positive Case | Regression | API Automation |
"""


def print_test_cases(
    title: str,
    test_cases: list[TestCase],
) -> None:

    print(f"\n{title}")

    for test_case in test_cases:
        print(
            f"{test_case.test_case_id} | "
            f"{test_case.module} | "
            f"{test_case.scenario}"
        )


def main():

    repository = TestCaseRepository(
        storage_path="data/test_case_repository_13_3_5.json"
    )

    repository.clear()

    parser = TestCaseParser()
    id_assigner = TestCaseIdAssigner()
    service = TestCaseService(
        repository=repository
    )

    # ---------------------------------------------------------
    # 1. Parse generated output from Chunk 1
    # ---------------------------------------------------------

    print("1. Parsing generated Chunk 1...")

    chunk_1_cases = parser.parse(
        GENERATED_CHUNK_1,
        source_document="BRD.docx",
    )

    print_test_cases(
        "Chunk 1 parsed test cases:",
        chunk_1_cases,
    )

    if len(chunk_1_cases) != 3:
        raise AssertionError(
            "Expected 3 test cases from Chunk 1."
        )

    # ---------------------------------------------------------
    # 2. Parse generated output from Chunk 2
    # ---------------------------------------------------------

    print("\n2. Parsing generated Chunk 2...")

    chunk_2_cases = parser.parse(
        GENERATED_CHUNK_2,
        source_document="BRD.docx",
    )

    print_test_cases(
        "Chunk 2 parsed test cases:",
        chunk_2_cases,
    )

    if len(chunk_2_cases) != 3:
        raise AssertionError(
            "Expected 3 test cases from Chunk 2."
        )

    # ---------------------------------------------------------
    # 3. Assign global IDs
    # ---------------------------------------------------------

    print("\n3. Assigning global Test Case IDs...")

    globally_assigned_cases = (
        id_assigner.assign_from_chunks(
            [
                chunk_1_cases,
                chunk_2_cases,
            ]
        )
    )

    print_test_cases(
        "Globally assigned test cases:",
        globally_assigned_cases,
    )

    expected_ids = [
        "TC001",
        "TC002",
        "TC003",
        "TC004",
        "TC005",
        "TC006",
    ]

    actual_ids = [
        test_case.test_case_id
        for test_case in globally_assigned_cases
    ]

    if actual_ids != expected_ids:
        raise AssertionError(
            "Global ID assignment failed.\n"
            f"Expected: {expected_ids}\n"
            f"Actual: {actual_ids}"
        )

    # ---------------------------------------------------------
    # 4. Save through TestCaseService
    # ---------------------------------------------------------

    print("\n4. Saving test cases through TestCaseService...")

    saved_cases = service.save_test_cases(
        globally_assigned_cases
    )

    print(
        "Saved test cases:",
        len(saved_cases),
    )

    if len(saved_cases) != 6:
        raise AssertionError(
            "Expected 6 saved test cases."
        )

    # ---------------------------------------------------------
    # 5. Verify repository contents
    # ---------------------------------------------------------

    print("\n5. Reading test cases from repository...")

    repository_cases = (
        service.get_all_test_cases()
    )

    print_test_cases(
        "Repository contents:",
        repository_cases,
    )

    if len(repository_cases) != 6:
        raise AssertionError(
            "Repository should contain 6 test cases."
        )

    repository_ids = [
        test_case.test_case_id
        for test_case in repository_cases
    ]

    if repository_ids != expected_ids:
        raise AssertionError(
            "Repository IDs do not match expected IDs."
        )

    # ---------------------------------------------------------
    # 6. Verify search
    # ---------------------------------------------------------

    print("\n6. Searching repository...")

    search_results = (
        service.search_test_cases(
            "CIBIL"
        )
    )

    print(
        "Search results:",
        len(search_results),
    )

    for test_case in search_results:
        print(
            f"{test_case.test_case_id} | "
            f"{test_case.scenario}"
        )

    if len(search_results) != 1:
        raise AssertionError(
            "Expected exactly one CIBIL search result."
        )

    if search_results[0].test_case_id != "TC005":
        raise AssertionError(
            "CIBIL test case should be TC005."
        )

    # ---------------------------------------------------------
    # 7. Verify individual retrieval
    # ---------------------------------------------------------

    print("\n7. Retrieving TC005...")

    retrieved_case = service.get_test_case(
        "TC005"
    )

    if retrieved_case is None:
        raise AssertionError(
            "TC005 could not be retrieved."
        )

    print(
        f"Retrieved: "
        f"{retrieved_case.test_case_id} | "
        f"{retrieved_case.scenario}"
    )

    if retrieved_case.scenario != "Validate CIBIL":
        raise AssertionError(
            "Retrieved TC005 contains unexpected data."
        )

    # ---------------------------------------------------------
    # 8. Verify source document
    # ---------------------------------------------------------

    print("\n8. Verifying source document metadata...")

    for test_case in repository_cases:

        if test_case.source_document != "BRD.docx":
            raise AssertionError(
                "Source document metadata was not preserved."
            )

    print(
        "Source document preserved: BRD.docx"
    )

    # ---------------------------------------------------------
    # 9. Final repository count
    # ---------------------------------------------------------

    print("\n9. Final repository count...")

    count = service.count()

    print(
        "Repository count:",
        count,
    )

    if count != 6:
        raise AssertionError(
            "Final repository count should be 6."
        )

    print(
        "\n13.3.5 generation → parsing → "
        "ID assignment → repository flow "
        "completed successfully."
    )


if __name__ == "__main__":
    main()