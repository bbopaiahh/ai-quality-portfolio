from pathlib import Path
from tempfile import TemporaryDirectory

from models.requirement import Requirement
from models.test_case import TestCase

from repository.requirement_repository import (
    RequirementRepository,
)
from repository.test_case_repository import (
    TestCaseRepository,
)
from repository.traceability_repository import (
    TraceabilityRepository,
)

from traceability.traceability_service import (
    TraceabilityService,
)


def create_requirement(
    requirement_id: str,
    module: str,
    requirement: str,
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        module=module,
        requirement=requirement,
        requirement_type="Functional",
        priority="P1",
        source_document="sample_brd.txt",
        source_reference=module,
    )


def create_test_case(
    test_case_id: str,
    module: str,
    scenario: str,
) -> TestCase:
    return TestCase(
        test_case_id=test_case_id,
        module=module,
        scenario=scenario,
        test_steps="Open application<br>Execute test",
        expected_result="Expected result is displayed",
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="UI Automation",
    )


def main():
    print("=" * 60)
    print("TRACEABILITY SERVICE MANUAL TEST")
    print("=" * 60)

    with TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        requirement_repository = (
            RequirementRepository(
                storage_path=str(
                    temp_path
                    / "requirements.json"
                )
            )
        )

        test_case_repository = (
            TestCaseRepository(
                storage_path=str(
                    temp_path
                    / "test_cases.json"
                )
            )
        )

        traceability_repository = (
            TraceabilityRepository(
                storage_path=str(
                    temp_path
                    / "traceability.json"
                )
            )
        )

        service = TraceabilityService(
            requirement_repository=(
                requirement_repository
            ),
            test_case_repository=(
                test_case_repository
            ),
            traceability_repository=(
                traceability_repository
            ),
        )

        # --------------------------------------------------
        # Prepare Requirements
        # --------------------------------------------------

        requirements = [
            create_requirement(
                "REQ001",
                "Lead Creation",
                "The system must create a valid lead.",
            ),
            create_requirement(
                "REQ002",
                "Eligibility",
                "The system must validate CIBIL.",
            ),
            create_requirement(
                "REQ003",
                "Documents",
                "Mandatory documents must be collected.",
            ),
        ]

        requirement_repository.save_many(
            requirements
        )

        print("Requirement test data: PASS")

        # --------------------------------------------------
        # Prepare Test Cases
        # --------------------------------------------------

        test_cases = [
            create_test_case(
                "TC001",
                "Lead Creation",
                "Create valid lead",
            ),
            create_test_case(
                "TC002",
                "Lead Creation",
                "Validate mandatory lead fields",
            ),
            create_test_case(
                "TC003",
                "Eligibility",
                "Validate CIBIL",
            ),
            create_test_case(
                "TC004",
                "Documents",
                "Validate mandatory documents",
            ),
        ]

        test_case_repository.save_many(
            test_cases
        )

        print("Test Case test data: PASS")

        # --------------------------------------------------
        # Test 1: Create single mapping
        # --------------------------------------------------

        mapping = service.create_mapping(
            requirement_id="REQ001",
            test_case_id="TC001",
        )

        assert mapping.requirement_id == "REQ001"
        assert mapping.test_case_id == "TC001"
        assert mapping.relationship_type == "COVERED"
        assert mapping.status == "ACTIVE"

        print("Create mapping: PASS")

        # --------------------------------------------------
        # Test 2: Create multiple mappings
        # --------------------------------------------------

        mappings = service.create_mappings(
            requirement_id="REQ001",
            test_case_ids=[
                "TC002",
            ],
        )

        assert len(mappings) == 1
        assert mappings[0].test_case_id == "TC002"

        print("Create multiple mappings: PASS")

        # --------------------------------------------------
        # Test 3: Get requirement mappings
        # --------------------------------------------------

        requirement_mappings = (
            service.get_requirement_mappings(
                "REQ001"
            )
        )

        assert len(requirement_mappings) == 2

        mapped_test_case_ids = {
            mapping.test_case_id
            for mapping in requirement_mappings
        }

        assert mapped_test_case_ids == {
            "TC001",
            "TC002",
        }

        print("Get requirement mappings: PASS")

        # --------------------------------------------------
        # Test 4: Get Test Case mappings
        # --------------------------------------------------

        test_case_mappings = (
            service.get_test_case_mappings(
                "TC001"
            )
        )

        assert len(test_case_mappings) == 1
        assert (
            test_case_mappings[0].requirement_id
            == "REQ001"
        )

        print("Get test case mappings: PASS")

        # --------------------------------------------------
        # Test 5: Get actual Test Case objects
        # --------------------------------------------------

        mapped_test_cases = (
            service.get_test_cases_for_requirement(
                "REQ001"
            )
        )

        assert len(mapped_test_cases) == 2

        mapped_ids = {
            test_case.test_case_id
            for test_case in mapped_test_cases
        }

        assert mapped_ids == {
            "TC001",
            "TC002",
        }

        print("Get test cases for requirement: PASS")

        # --------------------------------------------------
        # Test 6: Get actual Requirement objects
        # --------------------------------------------------

        requirement_objects = (
            service.get_requirements_for_test_case(
                "TC001"
            )
        )

        assert len(requirement_objects) == 1
        assert (
            requirement_objects[0].requirement_id
            == "REQ001"
        )

        print("Get requirements for test case: PASS")

        # --------------------------------------------------
        # Test 7: Requirement coverage
        # --------------------------------------------------

        assert service.is_requirement_covered(
            "REQ001"
        ) is True

        assert service.is_requirement_covered(
            "REQ002"
        ) is False

        assert service.is_requirement_covered(
            "REQ003"
        ) is False

        print("Requirement coverage check: PASS")

        # --------------------------------------------------
        # Test 8: Covered requirements
        # --------------------------------------------------

        covered = (
            service.get_covered_requirements()
        )

        covered_ids = {
            requirement.requirement_id
            for requirement in covered
        }

        assert covered_ids == {
            "REQ001",
        }

        print("Get covered requirements: PASS")

        # --------------------------------------------------
        # Test 9: Uncovered requirements
        # --------------------------------------------------

        uncovered = (
            service.get_uncovered_requirements()
        )

        uncovered_ids = {
            requirement.requirement_id
            for requirement in uncovered
        }

        assert uncovered_ids == {
            "REQ002",
            "REQ003",
        }

        print("Get uncovered requirements: PASS")

        # --------------------------------------------------
        # Test 10: Unmapped Test Cases
        # --------------------------------------------------

        unmapped = (
            service.get_unmapped_test_cases()
        )

        unmapped_ids = {
            test_case.test_case_id
            for test_case in unmapped
        }

        assert unmapped_ids == {
            "TC003",
            "TC004",
        }

        print("Get unmapped test cases: PASS")

        # --------------------------------------------------
        # Test 11: Coverage calculation
        # --------------------------------------------------

        coverage = (
            service.calculate_coverage()
        )

        assert (
            coverage["total_requirements"]
            == 3
        )

        assert (
            coverage["covered_requirements"]
            == 1
        )

        assert (
            coverage["uncovered_requirements"]
            == 2
        )

        assert (
            coverage["coverage_percentage"]
            == 33.33
        )

        print("Coverage calculation: PASS")

        # --------------------------------------------------
        # Test 12: Traceability matrix
        # --------------------------------------------------

        matrix = (
            service.get_traceability_matrix()
        )

        assert len(matrix) == 3

        matrix_by_id = {
            row["requirement_id"]: row
            for row in matrix
        }

        assert (
            matrix_by_id["REQ001"]["covered"]
            is True
        )

        assert (
            matrix_by_id["REQ002"]["covered"]
            is False
        )

        assert (
            matrix_by_id["REQ003"]["covered"]
            is False
        )

        assert (
            matrix_by_id["REQ001"]["test_case_ids"]
            == ["TC001", "TC002"]
        )

        print("Traceability matrix: PASS")

        # --------------------------------------------------
        # Test 13: Deactivate mapping
        # --------------------------------------------------

        deactivated = (
            service.deactivate_mapping(
                "REQ001",
                "TC002",
            )
        )

        assert deactivated.status == "INACTIVE"

        assert (
            service.is_requirement_covered(
                "REQ001"
            )
            is True
        )

        print("Deactivate mapping: PASS")

        # --------------------------------------------------
        # Test 14: Activate mapping
        # --------------------------------------------------

        activated = (
            service.activate_mapping(
                "REQ001",
                "TC002",
            )
        )

        assert activated.status == "ACTIVE"

        assert (
            service.is_requirement_covered(
                "REQ001"
            )
            is True
        )

        print("Activate mapping: PASS")

        # --------------------------------------------------
        # Test 15: Requirement validation
        # --------------------------------------------------

        try:
            service.create_mapping(
                requirement_id="REQ999",
                test_case_id="TC001",
            )

            raise AssertionError(
                "Non-existing Requirement was accepted."
            )

        except ValueError:
            pass

        print("Requirement validation: PASS")

        # --------------------------------------------------
        # Test 16: Test Case validation
        # --------------------------------------------------

        try:
            service.create_mapping(
                requirement_id="REQ002",
                test_case_id="TC999",
            )

            raise AssertionError(
                "Non-existing Test Case was accepted."
            )

        except ValueError:
            pass

        print("Test case validation: PASS")

        # --------------------------------------------------
        # Test 17: Duplicate mapping protection
        # --------------------------------------------------

        try:
            service.create_mapping(
                requirement_id="REQ001",
                test_case_id="TC001",
            )

            raise AssertionError(
                "Duplicate mapping was accepted."
            )

        except ValueError:
            pass

        print("Duplicate mapping protection: PASS")

    print("=" * 60)
    print(
        "All Traceability Service tests completed successfully."
    )
    print("=" * 60)


if __name__ == "__main__":
    main()