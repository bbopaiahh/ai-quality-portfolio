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

from coverage.coverage_report import CoverageReport


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
    print("COVERAGE REPORT MANUAL TEST")
    print("=" * 60)

    with TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        requirement_repository = (
            RequirementRepository(
                storage_path=str(
                    temp_path / "requirements.json"
                )
            )
        )

        test_case_repository = (
            TestCaseRepository(
                storage_path=str(
                    temp_path / "test_cases.json"
                )
            )
        )

        traceability_repository = (
            TraceabilityRepository(
                storage_path=str(
                    temp_path / "traceability.json"
                )
            )
        )

        traceability_service = TraceabilityService(
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

        coverage_report = CoverageReport(
            traceability_service
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
            create_requirement(
                "REQ004",
                "Sanction",
                "The system must generate sanction details.",
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
            create_test_case(
                "TC005",
                "Sanction",
                "Validate sanction details",
            ),
            create_test_case(
                "TC006",
                "Unrelated",
                "Validate unrelated scenario",
            ),
        ]

        test_case_repository.save_many(
            test_cases
        )

        print("Test Case test data: PASS")

        # --------------------------------------------------
        # Create Traceability
        #
        # REQ001 -> TC001, TC002
        # REQ002 -> TC003
        # REQ003 -> TC004
        # REQ004 -> no mapping
        # TC005, TC006 -> intentionally unmapped
        # --------------------------------------------------

        traceability_service.create_mapping(
            requirement_id="REQ001",
            test_case_id="TC001",
        )

        traceability_service.create_mapping(
            requirement_id="REQ001",
            test_case_id="TC002",
        )

        traceability_service.create_mapping(
            requirement_id="REQ002",
            test_case_id="TC003",
        )

        traceability_service.create_mapping(
            requirement_id="REQ003",
            test_case_id="TC004",
        )

        print("Traceability test data: PASS")

        # --------------------------------------------------
        # Test 1: Summary
        # --------------------------------------------------

        summary = (
            coverage_report.generate_summary()
        )

        assert (
            summary["total_requirements"]
            == 4
        )

        assert (
            summary["covered_requirements"]
            == 3
        )

        assert (
            summary["uncovered_requirements"]
            == 1
        )

        assert (
            summary["coverage_percentage"]
            == 75.0
        )

        print("Coverage summary: PASS")

        # --------------------------------------------------
        # Test 2: Covered Requirements
        # --------------------------------------------------

        covered = (
            coverage_report
            .get_covered_requirements()
        )

        covered_ids = {
            requirement.requirement_id
            for requirement in covered
        }

        assert covered_ids == {
            "REQ001",
            "REQ002",
            "REQ003",
        }

        print("Covered requirements: PASS")

        # --------------------------------------------------
        # Test 3: Uncovered Requirements
        # --------------------------------------------------

        uncovered = (
            coverage_report
            .get_uncovered_requirements()
        )

        uncovered_ids = {
            requirement.requirement_id
            for requirement in uncovered
        }

        assert uncovered_ids == {
            "REQ004",
        }

        print("Uncovered requirements: PASS")

        # --------------------------------------------------
        # Test 4: Unmapped Test Cases
        # --------------------------------------------------

        unmapped = (
            coverage_report
            .get_unmapped_test_cases()
        )

        unmapped_ids = {
            test_case.test_case_id
            for test_case in unmapped
        }

        assert unmapped_ids == {
            "TC005",
            "TC006",
        }

        print("Unmapped test cases: PASS")

        # --------------------------------------------------
        # Test 5: Coverage details
        # --------------------------------------------------

        details = (
            coverage_report
            .get_requirement_coverage_details()
        )

        assert len(details) == 4

        details_by_id = {
            row["requirement_id"]: row
            for row in details
        }

        assert (
            details_by_id["REQ001"]["covered"]
            is True
        )

        assert (
            details_by_id["REQ002"]["covered"]
            is True
        )

        assert (
            details_by_id["REQ003"]["covered"]
            is True
        )

        assert (
            details_by_id["REQ004"]["covered"]
            is False
        )

        assert (
            details_by_id["REQ001"]["test_case_ids"]
            == ["TC001", "TC002"]
        )

        assert (
            details_by_id["REQ004"]["test_case_ids"]
            == []
        )

        print("Coverage details: PASS")

        # --------------------------------------------------
        # Test 6: Complete report
        # --------------------------------------------------

        report = (
            coverage_report.generate_report()
        )

        assert "summary" in report
        assert "covered_requirements" in report
        assert "uncovered_requirements" in report
        assert "unmapped_test_cases" in report
        assert "details" in report

        assert (
            len(report["covered_requirements"])
            == 3
        )

        assert (
            len(report["uncovered_requirements"])
            == 1
        )

        assert (
            len(report["unmapped_test_cases"])
            == 2
        )

        assert len(report["details"]) == 4

        print("Complete report generation: PASS")

        # --------------------------------------------------
        # Test 7: Formatted text report
        # --------------------------------------------------

        text_report = (
            coverage_report
            .format_text_report()
        )

        assert (
            "Requirement Coverage Report"
            in text_report
        )

        assert (
            "Total Requirements      : 4"
            in text_report
        )

        assert (
            "Covered Requirements    : 3"
            in text_report
        )

        assert (
            "Uncovered Requirements  : 1"
            in text_report
        )

        assert (
            "Coverage Percentage     : 75.00%"
            in text_report
        )

        assert (
            "REQ004"
            in text_report
        )

        assert (
            "TC005"
            in text_report
        )

        print("Formatted text report: PASS")

        # --------------------------------------------------
        # Test 8: Print generated report
        # --------------------------------------------------

        print()
        print("-" * 60)
        print(text_report)
        print("-" * 60)

    print("=" * 60)
    print(
        "All Coverage Report tests completed successfully."
    )
    print("=" * 60)


if __name__ == "__main__":
    main()