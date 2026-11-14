from models.test_case import TestCase
from repository.test_case_repository import TestCaseRepository


def create_test_case(
    test_case_id: str,
    version: int = 1,
) -> TestCase:
    return TestCase(
        test_case_id=test_case_id,
        module="Lead Creation",
        scenario="Verify valid lead creation",
        test_steps=(
            "1. Open Lead Creation page<br>"
            "2. Enter valid lead details<br>"
            "3. Click Save"
        ),
        expected_result="Lead is created successfully.",
        priority="P1",
        test_type="Positive Case",
        suite_type="Smoke",
        automation_type="UI Automation",
        requirement_reference="BR-LEAD-001",
        version=version,
        status="ACTIVE",
        source_document="BRD.docx",
    )


def main():
    repository = TestCaseRepository(
        storage_path="data/test_repository_manual.json"
    )

    # Start with a clean repository.
    repository.clear()

    print("1. Saving test case...")

    tc001 = create_test_case("TC001")

    repository.save(tc001)

    print(
        "Saved:",
        repository.get_by_id("TC001").test_case_id,
    )

    print(
        "Repository count:",
        repository.count(),
    )

    print("\n2. Reading test case...")

    retrieved = repository.get_by_id("TC001")

    print(
        "ID:",
        retrieved.test_case_id,
    )

    print(
        "Version:",
        retrieved.version,
    )

    print(
        "Status:",
        retrieved.status,
    )

    print("\n3. Creating new version...")

    tc001_v2 = retrieved.create_new_version(
        scenario="Verify valid lead creation "
        "with updated business rule"
    )

    repository.update(tc001_v2)

    updated = repository.get_by_id("TC001")

    print(
        "ID:",
        updated.test_case_id,
    )

    print(
        "Version:",
        updated.version,
    )

    print(
        "Scenario:",
        updated.scenario,
    )

    print("\n4. Searching repository...")

    results = repository.search(
        "Lead Creation"
    )

    print(
        "Search results:",
        len(results),
    )

    for result in results:
        print(
            result.test_case_id,
            "v" + str(result.version),
        )

    print("\n5. Saving multiple test cases...")

    tc002 = create_test_case("TC002")
    tc003 = create_test_case("TC003")

    repository.save_many(
        [
            tc002,
            tc003,
        ]
    )

    print(
        "Repository count:",
        repository.count(),
    )

    print("\n6. Final repository contents...")

    for test_case in repository.get_all():
        print(
            test_case.test_case_id,
            "| version:",
            test_case.version,
            "| status:",
            test_case.status,
        )

    print("\nRepository test completed successfully.")


if __name__ == "__main__":
    main()