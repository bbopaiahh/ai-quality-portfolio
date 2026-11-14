from __future__ import annotations

from models.requirement import Requirement
from models.test_case import TestCase as RARETestCase
from repository.requirement_repository import RequirementRepository
from repository.test_case_change_detector import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    TestCaseChangeDetector,
)
from repository.test_case_repository import TestCaseRepository as RARETestCaseRepository
from repository.test_case_version_manager import TestCaseVersionManager as RARETestCaseVersionManager
from repository.traceability_repository import TraceabilityRepository
from traceability.traceability_service import TraceabilityService
from coverage.coverage_report import CoverageReport
from quality.test_suite_quality_analyzer import TestSuiteQualityAnalyzer as RARETestSuiteQualityAnalyzer


def build_requirement(
    requirement_id: str,
    requirement: str,
    priority: str = "P1",
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        module="Lead Management",
        requirement=requirement,
        requirement_type="Business Rule",
        priority=priority,
        source_document="integration_test_brd.txt",
        source_reference=requirement_id,
    )


def build_test_case(
    test_case_id: str,
    requirement_reference: str,
    scenario: str,
    expected_result: str,
    priority: str = "P1",
    test_type: str = "Positive Case",
    automation_type: str = "UI Automation",
) -> RARETestCase:
    return RARETestCase(
        test_case_id=test_case_id,
        module="Lead Management",
        scenario=scenario,
        test_steps="Open the lead screen.<br>Execute the scenario.<br>Verify the result.",
        expected_result=expected_result,
        priority=priority,
        test_type=test_type,
        suite_type="Regression",
        automation_type=automation_type,
        requirement_reference=requirement_reference,
    )


def test_rare_repository_to_quality_pipeline(tmp_path):
    """
    Phase 14 integration test.

    Proves that the core RARE repository pipeline works together:

        Requirements
            -> Test Case Repository
            -> Change Detection
            -> Version Management
            -> Traceability
            -> Coverage
            -> Quality Analysis

    All repositories use pytest's temporary directory so the real
    RARE data files are never modified.
    """

    # ------------------------------------------------------------
    # 1. Isolated repositories
    # ------------------------------------------------------------

    requirement_repository = RequirementRepository(
        storage_path=str(tmp_path / "requirements.json")
    )

    test_case_repository = RARETestCaseRepository(
        storage_path=str(tmp_path / "test_cases.json")
    )

    traceability_repository = TraceabilityRepository(
        storage_path=str(tmp_path / "traceability.json")
    )

    # ------------------------------------------------------------
    # 2. Seed requirements
    # ------------------------------------------------------------

    requirements = [
        build_requirement(
            "REQ001",
            "The system must create a valid lead.",
            priority="P0",
        ),
        build_requirement(
            "REQ002",
            "The system must validate the mobile number before lead creation.",
            priority="P1",
        ),
        build_requirement(
            "REQ003",
            "The system should display the lead creation confirmation.",
            priority="P2",
        ),
    ]

    requirement_repository.save_many(requirements)

    assert requirement_repository.count() == 3
    assert len(requirement_repository.get_all()) == 3

    # ------------------------------------------------------------
    # 3. Seed existing test cases
    # ------------------------------------------------------------

    existing_cases = [
        build_test_case(
            test_case_id="TC001",
            requirement_reference="REQ001",
            scenario="Create a valid lead",
            expected_result="Lead is created successfully.",
            priority="P0",
        ),
        build_test_case(
            test_case_id="TC002",
            requirement_reference="REQ002",
            scenario="Validate mobile number",
            expected_result="Valid mobile number is accepted.",
            priority="P1",
        ),
    ]

    test_case_repository.save_many(existing_cases)

    assert test_case_repository.count() == 2

    # ------------------------------------------------------------
    # 4. Simulate newly generated suite
    #
    # KEEP  -> TC001 remains unchanged
    # MODIFY -> TC002 expected result changes
    # ADD   -> new REQ003 test case
    # ------------------------------------------------------------

    generated_cases = [
        build_test_case(
            test_case_id="GEN001",
            requirement_reference="REQ001",
            scenario="Create a valid lead",
            expected_result="Lead is created successfully.",
            priority="P0",
        ),
        build_test_case(
            test_case_id="GEN002",
            requirement_reference="REQ002",
            scenario="Validate mobile number",
            expected_result="Invalid mobile number is rejected.",
            priority="P1",
            test_type="Negative Case",
        ),
        build_test_case(
            test_case_id="GEN003",
            requirement_reference="REQ003",
            scenario="Display lead creation confirmation",
            expected_result="Lead creation confirmation is displayed.",
            priority="P2",
        ),
    ]

    # ------------------------------------------------------------
    # 5. Change Detection
    # ------------------------------------------------------------

    change_detector = TestCaseChangeDetector()

    changes = change_detector.detect(
        new_test_cases=generated_cases,
        existing_test_cases=test_case_repository.get_all(),
    )

    change_summary = change_detector.summarize(changes)

    assert change_summary[KEEP] == 1
    assert change_summary[MODIFY] == 1
    assert change_summary[ADD] == 1
    assert change_summary[RETIRE] == 0

    # ------------------------------------------------------------
    # 6. Version Management
    # ------------------------------------------------------------

    version_manager = RARETestCaseVersionManager(
        repository=test_case_repository
    )

    affected_cases = version_manager.apply_changes(changes)

    assert len(affected_cases) == 3

    tc001 = test_case_repository.get_by_id("TC001")
    tc002 = test_case_repository.get_by_id("TC002")
    tc003 = test_case_repository.get_by_id("TC003")

    assert tc001 is not None
    assert tc001.version == 1
    assert tc001.status == "ACTIVE"

    assert tc002 is not None
    assert tc002.version == 2
    assert tc002.status == "ACTIVE"
    assert tc002.expected_result == "Invalid mobile number is rejected."

    assert tc003 is not None
    assert tc003.version == 1
    assert tc003.status == "ACTIVE"

    # The repository retains both the original and modified version.
    # TestCaseRepository does not expose a get_history() method; count()
    # includes stored historical records while get_all() exposes latest versions.
    assert test_case_repository.count() == 4
    assert len(test_case_repository.get_all()) == 3

    # ------------------------------------------------------------
    # 7. Traceability
    # ------------------------------------------------------------

    traceability_service = TraceabilityService(
        requirement_repository=requirement_repository,
        test_case_repository=test_case_repository,
        traceability_repository=traceability_repository,
    )

    traceability_service.create_mapping("REQ001", "TC001")
    traceability_service.create_mapping("REQ002", "TC002")
    traceability_service.create_mapping("REQ003", "TC003")

    assert traceability_repository.count() == 3

    req1_cases = traceability_service.get_test_cases_for_requirement("REQ001")
    req2_cases = traceability_service.get_test_cases_for_requirement("REQ002")
    req3_cases = traceability_service.get_test_cases_for_requirement("REQ003")

    assert [case.test_case_id for case in req1_cases] == ["TC001"]
    assert [case.test_case_id for case in req2_cases] == ["TC002"]
    assert [case.test_case_id for case in req3_cases] == ["TC003"]

    # ------------------------------------------------------------
    # 8. Coverage Analysis
    # ------------------------------------------------------------

    coverage_report = CoverageReport(
        traceability_service=traceability_service
    )

    coverage_summary = coverage_report.generate_summary()

    assert coverage_summary["total_requirements"] == 3
    assert coverage_summary["covered_requirements"] == 3
    assert coverage_summary["uncovered_requirements"] == 0
    assert coverage_summary["coverage_percentage"] == 100.0

    assert coverage_report.get_uncovered_requirements() == []
    assert coverage_report.get_unmapped_test_cases() == []

    # ------------------------------------------------------------
    # 9. Quality Analysis
    # ------------------------------------------------------------

    quality_analyzer = RARETestSuiteQualityAnalyzer()

    quality_result = quality_analyzer.analyze(
        requirements=requirement_repository.get_all(),
        test_cases=test_case_repository.get_all(),
        mappings=traceability_repository.get_all(),
    )

    summary = quality_result["summary"]

    assert summary["total_requirements"] == 3
    assert summary["total_test_cases"] == 3
    assert summary["critical_coverage_gaps"] == 0
    assert summary["requirements_requiring_review"] >= 0
    assert 0 <= summary["quality_score"] <= 100

    assert quality_result["priority_analysis"]["P0"]["total"] == 1
    assert quality_result["priority_analysis"]["P1"]["total"] == 1
    assert quality_result["priority_analysis"]["P2"]["total"] == 1

    assert quality_result["automation_analysis"]["automated_test_cases"] == 3
    assert quality_result["automation_analysis"]["automation_percentage"] == 100.0

    # ------------------------------------------------------------
    # 10. Final repository state
    # ------------------------------------------------------------

    final_test_cases = test_case_repository.get_all()

    assert len(final_test_cases) == 3
    assert {case.test_case_id for case in final_test_cases} == {
        "TC001",
        "TC002",
        "TC003",
    }

    assert all(case.status == "ACTIVE" for case in final_test_cases)

    # The real project repositories were never touched because every
    # repository above points to tmp_path.
    print("Phase 14 integration pipeline: PASS")
    print(f"Requirements: {len(requirement_repository.get_all())}")
    print(f"Active test cases: {len(final_test_cases)}")
    print(f"Coverage: {coverage_summary['coverage_percentage']:.2f}%")
    print(f"Quality score: {summary['quality_score']:.2f}")
