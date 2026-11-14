from repository.test_case_parser import TestCaseParser
from repository.test_case_service import TestCaseService


SAMPLE_OUTPUT = """
| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|
| TC001 | Lead Creation | Create valid lead | 1. Open Lead page<br>2. Enter valid data<br>3. Click Save | Lead is created successfully | P1 | Positive Case | Smoke | UI Automation |
| TC002 | Lead Creation | Reject invalid mobile | 1. Open Lead page<br>2. Enter invalid mobile<br>3. Click Save | Validation message is displayed | P1 | Negative Case | Sanity | UI Automation |
| TC003 | Eligibility | Validate CIBIL threshold | 1. Enter CIBIL score | Eligibility result is calculated correctly | P1 | Edge Case | Regression | Backend/DB |
"""


def main():

    parser = TestCaseParser()

    service = TestCaseService()

    # Use a clean development repository for this test.
    service.repository.clear()

    print("1. Parsing generated Markdown...")

    test_cases = parser.parse(
        SAMPLE_OUTPUT,
        source_document="BRD.docx",
    )

    print(
        "Parsed test cases:",
        len(test_cases),
    )

    for test_case in test_cases:
        print(
            test_case.test_case_id,
            "|",
            test_case.module,
        )

    print("\n2. Saving parsed test cases...")

    service.save_test_cases(
        test_cases
    )

    print(
        "Repository count:",
        service.count(),
    )

    print("\n3. Reading from repository...")

    stored = service.get_all_test_cases()

    for test_case in stored:

        print(
            test_case.test_case_id,
            "| version:",
            test_case.version,
            "| status:",
            test_case.status,
            "| source:",
            test_case.source_document,
        )

    print("\n4. Searching repository...")

    results = service.search_test_cases(
        "Eligibility"
    )

    print(
        "Search results:",
        len(results),
    )

    for result in results:
        print(
            result.test_case_id,
            "|",
            result.scenario,
        )

    print(
        "\nRepository integration test "
        "completed successfully."
    )


if __name__ == "__main__":
    main()