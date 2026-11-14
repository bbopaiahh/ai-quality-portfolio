from models.test_case import TestCase
from repository.test_case_change_detector import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    TestCaseChange,
)
from repository.test_case_repository import (
    TestCaseRepository,
)
from repository.test_case_version_manager import (
    TestCaseVersionManager,
)


def create_test_case(
    test_case_id: str,
    module: str,
    scenario: str,
    test_steps: str,
    expected_result: str,
    version: int = 1,
    status: str = "ACTIVE",
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
        version=version,
        status=status,
        source_document="BRD.docx",
    )


def main():

    repository = TestCaseRepository(
        storage_path=(
            "data/test_case_version_manager_manual.json"
        )
    )

    repository.clear()

    # ========================================================
    # 1. Create initial repository
    # ========================================================

    print("1. Creating initial repository...")

    initial_cases = [

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

    repository.save_many(
        initial_cases
    )

    print(
        "Initial repository count:",
        repository.count(),
    )

    # ========================================================
    # 2. Create detected changes
    # ========================================================

    print("\n2. Creating detected changes...")

    existing_tc001 = repository.get_by_id(
        "TC001"
    )

    existing_tc002 = repository.get_by_id(
        "TC002"
    )

    existing_tc003 = repository.get_by_id(
        "TC003"
    )

    existing_tc004 = repository.get_by_id(
        "TC004"
    )

    changes = [

        # KEEP
        TestCaseChange(
            action=KEEP,
            test_case_id="TC001",
            new_test_case=existing_tc001,
            existing_test_case=existing_tc001,
            reason="No changes.",
        ),

        # MODIFY
        TestCaseChange(
            action=MODIFY,
            test_case_id="TC002",
            new_test_case=create_test_case(
                "TC001",
                "Lead Creation",
                "Validate mobile number",
                "1. Open Lead page<br>"
                "2. Enter 10 digit mobile number<br>"
                "3. Save lead",
                "System validates the mobile number "
                "and displays the result.",
            ),
            existing_test_case=existing_tc002,
            reason="Test case content changed.",
        ),

        # KEEP
        TestCaseChange(
            action=KEEP,
            test_case_id="TC003",
            new_test_case=existing_tc003,
            existing_test_case=existing_tc003,
            reason="No changes.",
        ),

        # ADD
        TestCaseChange(
            action=ADD,
            test_case_id=None,
            new_test_case=create_test_case(
                "TC001",
                "Document Checklist",
                "Validate mandatory documents",
                "1. Upload mandatory documents<br>"
                "2. Submit documents",
                "Mandatory documents are validated.",
            ),
            existing_test_case=None,
            reason="New test case.",
        ),

        # RETIRE
        TestCaseChange(
            action=RETIRE,
            test_case_id="TC004",
            new_test_case=None,
            existing_test_case=existing_tc004,
            reason="Test case no longer exists.",
        ),
    ]

    print(
        "Changes prepared:",
        len(changes),
    )

    # ========================================================
    # 3. Apply version management
    # ========================================================

    print(
        "\n3. Applying version management..."
    )

    manager = TestCaseVersionManager(
        repository=repository
    )

    affected_cases = (
        manager.apply_changes(
            changes
        )
    )

    print(
        "Affected cases:",
        len(affected_cases),
    )

    # ========================================================
    # 4. Verify TC001 KEEP
    # ========================================================

    print(
        "\n4. Verifying KEEP..."
    )

    tc001 = repository.get_by_id(
        "TC001"
    )

    if tc001 is None:
        raise AssertionError(
            "TC001 should exist."
        )

    if tc001.version != 1:
        raise AssertionError(
            "TC001 should remain version 1."
        )

    if tc001.status != "ACTIVE":
        raise AssertionError(
            "TC001 should remain ACTIVE."
        )

    print(
        f"TC001 | v{tc001.version} | "
        f"{tc001.status}"
    )

    # ========================================================
    # 5. Verify TC002 MODIFY
    # ========================================================

    print(
        "\n5. Verifying MODIFY..."
    )

    tc002 = repository.get_by_id(
        "TC002"
    )

    if tc002 is None:
        raise AssertionError(
            "TC002 should exist."
        )

    if tc002.version != 2:
        raise AssertionError(
            "TC002 should be version 2."
        )

    if tc002.status != "ACTIVE":
        raise AssertionError(
            "TC002 v2 should be ACTIVE."
        )

    if "10 digit" not in tc002.test_steps:
        raise AssertionError(
            "TC002 v2 should contain "
            "the updated test steps."
        )

    print(
        f"TC002 | v{tc002.version} | "
        f"{tc002.status}"
    )

    # ========================================================
    # 6. Verify TC003 KEEP
    # ========================================================

    print(
        "\n6. Verifying second KEEP..."
    )

    tc003 = repository.get_by_id(
        "TC003"
    )

    if tc003 is None:
        raise AssertionError(
            "TC003 should exist."
        )

    if tc003.version != 1:
        raise AssertionError(
            "TC003 should remain version 1."
        )

    print(
        f"TC003 | v{tc003.version} | "
        f"{tc003.status}"
    )

    # ========================================================
    # 7. Verify TC004 RETIRE
    # ========================================================

    print(
        "\n7. Verifying RETIRE..."
    )

    tc004 = repository.get_by_id(
        "TC004"
    )

    if tc004 is None:
        raise AssertionError(
            "TC004 should exist."
        )

    if tc004.version != 2:
        raise AssertionError(
            "TC004 should be version 2."
        )

    if tc004.status != "RETIRED":
        raise AssertionError(
            "TC004 should be RETIRED."
        )

    print(
        f"TC004 | v{tc004.version} | "
        f"{tc004.status}"
    )

    # ========================================================
    # 8. Verify ADD
    # ========================================================

    print(
        "\n8. Verifying ADD..."
    )

    tc005 = repository.get_by_id(
        "TC005"
    )

    if tc005 is None:
        raise AssertionError(
            "New test case should receive TC005."
        )

    if tc005.version != 1:
        raise AssertionError(
            "TC005 should start at version 1."
        )

    if tc005.status != "ACTIVE":
        raise AssertionError(
            "TC005 should be ACTIVE."
        )

    print(
        f"TC005 | v{tc005.version} | "
        f"{tc005.status}"
    )

    # ========================================================
    # 9. Verify repository history
    # ========================================================

    print(
        "\n9. Verifying repository history..."
    )

    raw_data = repository._read_data()

    tc002_versions = [
        record
        for record in raw_data
        if record["test_case_id"] == "TC002"
    ]

    tc004_versions = [
        record
        for record in raw_data
        if record["test_case_id"] == "TC004"
    ]

    if len(tc002_versions) != 2:
        raise AssertionError(
            "TC002 should have two stored versions."
        )

    if len(tc004_versions) != 2:
        raise AssertionError(
            "TC004 should have two stored versions."
        )

    print(
        "TC002 stored versions:",
        len(tc002_versions),
    )

    print(
        "TC004 stored versions:",
        len(tc004_versions),
    )

    # ========================================================
    # 10. Final repository state
    # ========================================================

    print(
        "\n10. Final repository state..."
    )

    final_cases = repository.get_all()

    for test_case in sorted(
        final_cases,
        key=lambda case: case.test_case_id,
    ):

        print(
            f"{test_case.test_case_id} | "
            f"v{test_case.version} | "
            f"{test_case.status} | "
            f"{test_case.scenario}"
        )

    print(
        "\n13.5.2 Version Manager test "
        "completed successfully."
    )


if __name__ == "__main__":
    main()