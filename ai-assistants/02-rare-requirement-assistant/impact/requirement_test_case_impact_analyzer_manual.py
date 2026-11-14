from pathlib import Path
from tempfile import TemporaryDirectory

from impact.requirement_test_case_impact_analyzer import (
    IMPACTED,
    RequirementTestCaseImpactAnalyzer,
)
from models.requirement import Requirement
from models.test_case import TestCase
from repository.requirement_repository import RequirementRepository
from repository.test_case_repository import TestCaseRepository
from repository.traceability_repository import TraceabilityRepository
from traceability.traceability_service import TraceabilityService


def create_requirement(
    requirement_id: str,
    version: int,
    requirement_text: str,
) -> Requirement:
    """
    Create a Requirement for the manual test.
    """

    return Requirement(
        requirement_id=requirement_id,
        module="Test Module",
        requirement=requirement_text,
        requirement_type="Functional",
        priority="P1",
        source_document="impact_test.docx",
        source_reference=f"Section {requirement_id}",
        version=version,
        status="ACTIVE",
    )


def create_test_case(
    test_case_id: str,
    title: str,
) -> TestCase:
    """
    Create a Test Case for the manual test.
    """

    return TestCase(
        test_case_id=test_case_id,
        module="Test Module",
        scenario=title,
        test_steps="1. Execute the test",
        expected_result="Expected result is displayed",
        priority="P1",
        test_type="Functional",
        suite_type="Regression",
        automation_type="Manual",
        pre_condition="System is available",
        requirement_reference=None,
    )


def run_manual_test() -> None:
    """
    Validate Requirement -> Test Case Impact Analysis.
    """

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        requirement_repository = RequirementRepository(
            storage_path=str(
                temp_path / "requirements.json"
            )
        )

        test_case_repository = TestCaseRepository(
            storage_path=str(
                temp_path / "test_cases.json"
            )
        )

        traceability_repository = TraceabilityRepository(
            storage_path=str(
                temp_path / "traceability.json"
            )
        )

        traceability_service = TraceabilityService(
            requirement_repository=requirement_repository,
            test_case_repository=test_case_repository,
            traceability_repository=traceability_repository,
        )

        analyzer = RequirementTestCaseImpactAnalyzer(
            traceability_service=traceability_service
        )

        # --------------------------------------------------
        # Create Requirements
        # --------------------------------------------------

        req001_v1 = create_requirement(
            requirement_id="REQ001",
            version=1,
            requirement_text=(
                "Customer must provide a valid account number."
            ),
        )

        req002_v1 = create_requirement(
            requirement_id="REQ002",
            version=1,
            requirement_text=(
                "Customer must provide a valid mobile number."
            ),
        )

        requirement_repository.save(req001_v1)
        requirement_repository.save(req002_v1)

        # --------------------------------------------------
        # Create Test Cases
        # --------------------------------------------------

        tc001 = create_test_case(
            test_case_id="TC001",
            title="Validate account number",
        )

        tc002 = create_test_case(
            test_case_id="TC002",
            title="Validate invalid account number",
        )

        tc003 = create_test_case(
            test_case_id="TC003",
            title="Validate mobile number",
        )

        test_case_repository.save(tc001)
        test_case_repository.save(tc002)
        test_case_repository.save(tc003)

        # --------------------------------------------------
        # Create Traceability
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

        # --------------------------------------------------
        # Create changed Requirement
        # --------------------------------------------------

        req001_v2 = req001_v1.create_new_version(
            requirement=(
                "Customer must provide a valid account number "
                "and account status must be ACTIVE."
            ),
            priority="P1",
        )

        requirement_repository.save_version(req001_v2)

        # --------------------------------------------------
        # Analyze impact
        # --------------------------------------------------

        impacts = analyzer.analyze_requirement_change(
            previous_requirement=req001_v1,
            current_requirement=req001_v2,
        )

        print()
        print("=" * 70)
        print("Requirement → Test Case Impact Analysis")
        print("=" * 70)

        for impact in impacts:
            print(
                f"{impact.requirement_id} | "
                f"{impact.test_case_id} | "
                f"{impact.impact_status} | "
                f"v{impact.previous_requirement_version}"
                f" -> "
                f"v{impact.current_requirement_version}"
            )
            print(f"Reason: {impact.reason}")

        # --------------------------------------------------
        # Assertions
        # --------------------------------------------------

        assert len(impacts) == 2, (
            "REQ001 should impact exactly two Test Cases."
        )

        impacted_test_case_ids = {
            impact.test_case_id
            for impact in impacts
        }

        assert impacted_test_case_ids == {
            "TC001",
            "TC002",
        }, (
            "Only TC001 and TC002 should be impacted."
        )

        assert all(
            impact.impact_status == IMPACTED
            for impact in impacts
        ), (
            "All impacted Test Cases must have IMPACTED status."
        )

        assert all(
            impact.previous_requirement_version == 1
            for impact in impacts
        )

        assert all(
            impact.current_requirement_version == 2
            for impact in impacts
        )

        # --------------------------------------------------
        # Verify unrelated Requirement
        # --------------------------------------------------

        req002_impacts = analyzer.analyze_requirement_change(
            previous_requirement=req002_v1,
            current_requirement=req002_v1.create_new_version(
                requirement=(
                    "Customer must provide a valid mobile number "
                    "and mobile number must be verified."
                )
            ),
        )

        req002_test_case_ids = {
            impact.test_case_id
            for impact in req002_impacts
        }

        assert req002_test_case_ids == {
            "TC003",
        }, (
            "REQ002 should impact only TC003."
        )

        # --------------------------------------------------
        # Verify no traceability = no impact
        # --------------------------------------------------

        req003_v1 = create_requirement(
            requirement_id="REQ003",
            version=1,
            requirement_text="Customer must accept the terms.",
        )

        req003_v2 = req003_v1.create_new_version(
            requirement=(
                "Customer must explicitly accept the updated terms."
            )
        )

        requirement_repository.save(req003_v1)
        requirement_repository.save_version(req003_v2)

        req003_impacts = analyzer.analyze_requirement_change(
            previous_requirement=req003_v1,
            current_requirement=req003_v2,
        )

        assert req003_impacts == [], (
            "A Requirement without active Test Case "
            "traceability should produce no impacts."
        )

        assert (
            analyzer.is_requirement_change_impacting_test_cases(
                previous_requirement=req001_v1,
                current_requirement=req001_v2,
            )
            is True
        )

        assert (
            analyzer.is_requirement_change_impacting_test_cases(
                previous_requirement=req003_v1,
                current_requirement=req003_v2,
            )
            is False
        )

        # --------------------------------------------------
        # Verify actual Test Case retrieval
        # --------------------------------------------------

        affected_test_cases = (
            analyzer.get_affected_test_cases(
                previous_requirement=req001_v1,
                current_requirement=req001_v2,
            )
        )

        affected_ids = {
            test_case.test_case_id
            for test_case in affected_test_cases
        }

        assert affected_ids == {
            "TC001",
            "TC002",
        }

        print()
        print("All Requirement → Test Case impact checks passed.")
        print()
        print("Verified:")
        print("  ✓ Changed Requirement identified")
        print("  ✓ Active traceability used")
        print("  ✓ TC001 identified as impacted")
        print("  ✓ TC002 identified as impacted")
        print("  ✓ TC003 correctly excluded")
        print("  ✓ Unmapped Requirement produces no impact")
        print("  ✓ Version 1 → Version 2 recorded")
        print("  ✓ Actual affected Test Cases retrieved")
        print()
        print("Manual impact analysis test PASSED.")
        print("=" * 70)


if __name__ == "__main__":
    run_manual_test()