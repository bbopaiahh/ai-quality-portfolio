from pathlib import Path
from tempfile import TemporaryDirectory

from models.test_case import TestCase
from repository.test_case_change_detector import MODIFY, KEEP, ADD, TestCaseChangeDetector
from repository.test_case_repository import TestCaseRepository
from repository.test_case_version_manager import TestCaseVersionManager


def make_case(test_case_id, scenario, pre_condition, version=1):
    return TestCase(
        test_case_id=test_case_id,
        module="Generic Module",
        scenario=scenario,
        test_steps="1. Perform the action",
        expected_result="Expected result is displayed",
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="Manual",
        pre_condition=pre_condition,
        requirement_reference=("REQ-001" if scenario == "Verify record access" else "REQ-002"),
        version=version,
        source_document="sample.docx",
    )


def main():
    # Case 1: a pre-condition-only change must be detected as MODIFY.
    detector = TestCaseChangeDetector()
    old_case = make_case("TC001", "Verify record access", "User is logged in")
    changed_case = make_case(
        "TC999", "Verify record access", "User is logged in as an administrator"
    )
    changes = detector.detect_changes([changed_case], [old_case])
    assert len(changes) == 1, changes
    assert changes[0].action == MODIFY, changes[0].action
    assert changes[0].existing_test_case.test_case_id == "TC001"

    # Case 2: unchanged pre-condition remains KEEP.
    unchanged = make_case("TC999", "Verify record access", "User is logged in")
    keep_changes = detector.detect_changes([unchanged], [old_case])
    assert keep_changes[0].action == KEEP, keep_changes[0].action

    with TemporaryDirectory() as temp_dir:
        storage = str(Path(temp_dir) / "repository.json")
        repository = TestCaseRepository(storage_path=storage)
        repository.save(old_case)
        manager = TestCaseVersionManager(repository=repository)

        # Case 3: MODIFY must store the incoming pre-condition on v2.
        modified = manager.apply_changes(changes)
        assert len(modified) == 1
        assert modified[0].test_case_id == "TC001"
        assert modified[0].version == 2
        assert modified[0].pre_condition == "User is logged in as an administrator"
        history = repository._read_data()
        assert [row["version"] for row in history if row["test_case_id"] == "TC001"] == [1, 2]

        # Case 4: ADD must store its incoming pre-condition.
        add_case = TestCase(
            test_case_id="GENERATED-ID",
            module="Archive Export",
            scenario="Create compressed archive of completed reports",
            test_steps="1. Generate a downloadable ZIP archive of report bundles",
            expected_result="A ZIP archive is created and saved to disk",
            priority="P2",
            test_type="Positive Case",
            suite_type="Regression",
            automation_type="Manual",
            pre_condition="Export permission is granted",
            requirement_reference="REQ-NEW",
            source_document="sample.docx",
        )
        detected_additions = detector.detect_changes([add_case], repository.get_all())
        add_changes = [change for change in detected_additions if change.action == ADD]
        assert len(add_changes) == 1, detected_additions
        added = manager.apply_changes(add_changes)
        assert len(added) == 1
        assert added[0].test_case_id == "TC002"
        assert added[0].version == 1
        assert added[0].pre_condition == "Export permission is granted"

        # Case 5: latest version remains retrievable.
        latest = repository.get_by_id("TC001")
        assert latest is not None and latest.version == 2
        assert latest.pre_condition == "User is logged in as an administrator"

    print("PASS: pre-condition-only changes are MODIFY")
    print("PASS: unchanged cases remain KEEP")
    print("PASS: MODIFY preserves the incoming pre-condition and creates v2")
    print("PASS: ADD preserves the incoming pre-condition")
    print("PASS: repository history and latest-version retrieval remain correct")


if __name__ == "__main__":
    main()
