"""Manual verification for repository version, validation, and persistence integrity.

Run from the RARE project root:
    python repository/test_case_repository_manual.py
"""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.test_case import TestCase as CaseModel
from repository.test_case_repository import TestCaseRepository as CaseRepository
from repository.test_case_version_manager import TestCaseVersionManager as CaseVersionManager
from repository.test_case_change_detector import RETIRE, TestCaseChange as ChangeRecord


def make_case(
    test_case_id: str,
    version: int = 1,
    status: str = "ACTIVE",
) -> CaseModel:
    return CaseModel(
        test_case_id=test_case_id,
        module="Sample Module",
        scenario=f"Scenario {test_case_id} v{version}",
        test_steps="1. Perform the action",
        expected_result="Expected outcome is observed",
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="Manual",
        pre_condition="User has valid access",
        requirement_reference="REQ001",
        version=version,
        status=status,
        source_document="sample_brd.docx",
    )


def expect_value_error(callback, label: str) -> None:
    try:
        callback()
    except ValueError:
        print(f"PASS: {label}")
        return
    raise AssertionError(f"Expected ValueError: {label}")


def expect_runtime_error(callback, label: str) -> None:
    try:
        callback()
    except RuntimeError:
        print(f"PASS: {label}")
        return
    raise AssertionError(f"Expected RuntimeError: {label}")


def write_raw(storage: Path, data) -> None:
    storage.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def raw_case(test_case_id: str = "TC_BAD", version=1) -> dict:
    return {
        "test_case_id": test_case_id,
        "module": "Sample Module",
        "scenario": "Sample scenario",
        "test_steps": "Perform the action",
        "expected_result": "Expected outcome",
        "priority": "P1",
        "test_type": "Positive Case",
        "suite_type": "Regression",
        "automation_type": "Manual",
        "version": version,
        "status": "ACTIVE",
        "created_at": "2026-01-01T10:00:00",
        "updated_at": "2026-01-01T10:00:00",
    }


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        storage = Path(temp_dir) / "test_cases.json"
        repository = CaseRepository(storage_path=str(storage))
        repository.save(make_case("TC001", 1))

        repository.update(make_case("TC001", 2))
        assert repository.get_by_id("TC001").version == 2
        print("PASS: next sequential version (v2 after v1) is accepted")

        before = storage.read_text(encoding="utf-8")
        expect_value_error(
            lambda: repository.update(make_case("TC001", 2)),
            "duplicate incoming version is rejected",
        )
        assert storage.read_text(encoding="utf-8") == before
        print("PASS: duplicate version rejection leaves history unchanged")

        expect_value_error(
            lambda: repository.update(make_case("TC001", 4)),
            "skipped incoming version is rejected",
        )
        assert storage.read_text(encoding="utf-8") == before
        print("PASS: skipped version rejection leaves history unchanged")

        expect_value_error(
            lambda: repository.update(make_case("TC001", 1)),
            "stale version is rejected",
        )

        expect_value_error(
            lambda: repository.update(make_case("TC999", 2)),
            "unknown ID is rejected",
        )

        for invalid_version in (0, -1, True, 2.5, "3"):
            expect_value_error(
                lambda v=invalid_version: repository.update(
                    make_case("TC001", v)
                ),
                f"invalid incoming version {invalid_version!r} is rejected",
            )
        print("PASS: unknown IDs and invalid incoming versions are rejected")

        manager = CaseVersionManager(repository=repository)
        latest = repository.get_by_id("TC001")
        retired = manager._apply_retire(
            ChangeRecord(
                action=RETIRE,
                test_case_id="TC001",
                existing_test_case=latest,
            )
        )
        assert retired.version == 3
        assert retired.status == "RETIRED"
        assert repository.count() == 3
        assert repository.get_by_id("TC001").version == 3
        print("PASS: RETIRE creates the next version and preserves history")

        # Simulate a failed serialization/write. The existing file must survive.
        before_bytes = storage.read_bytes()
        with patch(
            "repository.test_case_repository.json.dump",
            side_effect=OSError("simulated write failure"),
        ):
            try:
                repository._write_data([])
            except OSError:
                pass
            else:
                raise AssertionError("Expected simulated write failure")

        assert storage.read_bytes() == before_bytes
        assert json.loads(storage.read_text(encoding="utf-8"))[-1]["version"] == 3
        assert not list(storage.parent.glob(f".{storage.name}.*.tmp"))
        print(
            "PASS: failed JSON write preserves repository data "
            "and cleans up the temporary file"
        )

        repository.update(make_case("TC001", 4))
        assert repository.get_by_id("TC001").version == 4
        print("PASS: successful writes still work after atomic-write change")

        # Malformed JSON syntax must be rejected without rewriting the file.
        storage.write_text("{ invalid JSON", encoding="utf-8")
        malformed_json_before = storage.read_bytes()
        expect_runtime_error(repository.count, "malformed JSON syntax")
        assert storage.read_bytes() == malformed_json_before
        print("PASS: malformed JSON is rejected without modifying the file")

        # Validation: non-object records, missing fields, invalid versions,
        # duplicate/gapped histories, and malformed timestamps.
        invalid_cases = []

        invalid_cases.append(
            ("non-object record", ["not a record"])
        )

        missing_required = raw_case()
        del missing_required["expected_result"]
        invalid_cases.append(
            ("missing required field", [missing_required])
        )

        for invalid_version in (0, -1, True, 1.5, "2", None):
            invalid_cases.append(
                (
                    f"invalid stored version {invalid_version!r}",
                    [raw_case(version=invalid_version)],
                )
            )

        duplicate_history = [
            raw_case("TC_DUP", 1),
            raw_case("TC_DUP", 1),
        ]
        invalid_cases.append(
            ("duplicate historical versions", duplicate_history)
        )

        skipped_history = [
            raw_case("TC_GAP", 1),
            raw_case("TC_GAP", 3),
        ]
        invalid_cases.append(
            ("skipped historical version", skipped_history)
        )

        malformed_timestamp = raw_case()
        malformed_timestamp["created_at"] = "not-a-timestamp"
        invalid_cases.append(
            ("malformed timestamp", [malformed_timestamp])
        )

        non_string_timestamp = raw_case()
        non_string_timestamp["updated_at"] = 123
        invalid_cases.append(
            ("non-string timestamp", [non_string_timestamp])
        )

        for label, payload in invalid_cases:
            write_raw(storage, payload)
            before_invalid_read = storage.read_bytes()
            expect_runtime_error(
                repository.count,
                label,
            )
            assert storage.read_bytes() == before_invalid_read
            print(f"PASS: invalid repository data remains unchanged ({label})")

        # Legacy defaults remain supported: absent optional/defaulted fields,
        # including version and timestamps, are interpreted by the model.
        legacy_case = {
            "test_case_id": "TC_LEGACY",
            "module": "Legacy Module",
            "scenario": "Legacy scenario",
            "test_steps": "Perform the action",
            "expected_result": "Expected outcome",
            "priority": "P2",
            "test_type": "Positive Case",
            "suite_type": "Regression",
            "automation_type": "Manual",
        }
        write_raw(storage, [legacy_case])
        loaded_legacy = repository.get_by_id("TC_LEGACY")
        assert loaded_legacy.version == 1
        assert loaded_legacy.status == "ACTIVE"
        assert loaded_legacy.pre_condition == ""
        assert loaded_legacy.created_at is not None
        assert loaded_legacy.updated_at is not None
        print("PASS: legacy records continue to use TestCase model defaults")

    print("ALL REPOSITORY INTEGRITY CHECKS PASSED")


if __name__ == "__main__":
    main()
