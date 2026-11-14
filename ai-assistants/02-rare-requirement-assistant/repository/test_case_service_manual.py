"""Manual verification for test-case service count semantics.

Run from the RARE project root:
    python repository/test_case_service_manual.py
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.test_case import TestCase as CaseModel
from repository.test_case_repository import TestCaseRepository as CaseRepository
from repository.test_case_service import TestCaseService as CaseService


def make_case(test_case_id: str, version: int = 1) -> CaseModel:
    return CaseModel(
        test_case_id=test_case_id,
        module="Sample Module",
        scenario=f"Scenario for {test_case_id} v{version}",
        test_steps="1. Perform the action",
        expected_result="Expected outcome is observed",
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="Manual",
        requirement_reference="REQ001",
        version=version,
        status="ACTIVE",
        source_document="sample_brd.docx",
    )


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        storage_path = str(Path(temp_dir) / "test_cases.json")
        repository = CaseRepository(storage_path=storage_path)
        service = CaseService(repository=repository)

        repository.save(make_case("TC001", version=1))
        repository.update(make_case("TC001", version=2))
        repository.save(make_case("TC002", version=1))

        assert service.count() == 2, (
            f"Expected 2 unique test cases, got {service.count()}"
        )
        print("PASS: service.count() returns unique test-case count (2)")

        assert service.count_records() == 3, (
            f"Expected 3 stored records, got {service.count_records()}"
        )
        print("PASS: service.count_records() includes history (3 records)")

        assert len(service.get_all_test_cases()) == 2
        print("PASS: get_all_test_cases() returns latest version per ID")

        assert service.get_test_case("TC001").version == 2
        print("PASS: get_test_case() returns the latest version (v2)")

        print("ALL PHASE 4 STEP 3 CHECKS PASSED")


if __name__ == "__main__":
    main()
