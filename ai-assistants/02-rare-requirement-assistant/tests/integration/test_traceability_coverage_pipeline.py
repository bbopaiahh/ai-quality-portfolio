from __future__ import annotations

from models.requirement import Requirement
from models.test_case import TestCase
from models.traceability import Traceability
from repository.requirement_repository import RequirementRepository
from repository.test_case_repository import TestCaseRepository
from repository.traceability_repository import (
    TraceabilityRepository,
)
from traceability.traceability_service import (
    TraceabilityService,
)
from coverage.coverage_report import CoverageReport


def build_requirement(
    requirement_id: str,
    requirement: str,
    module: str = "Lead Management",
) -> Requirement:
    """
    Build a deterministic Requirement for integration testing.
    """

    return Requirement(
        requirement_id=requirement_id,
        module=module,
        requirement=requirement,
        requirement_type="Functional",
        priority="P1",
        source_document="coverage_integration_fsd.txt",
        status="ACTIVE",
        version=1,
    )


def build_test_case(
    test_case_id: str,
    scenario: str,
    requirement_reference: str | None = None,
) -> TestCase:
    """
    Build a deterministic TestCase for integration testing.
    """

    return TestCase(
        test_case_id=test_case_id,
        module="Lead Management",
        scenario=scenario,
        test_steps=(
            "Open the Lead Management screen.<br>"
            "Perform the required action.<br>"
            "Verify the result."
        ),
        expected_result="Expected behavior is displayed correctly.",
        priority="P1",
        test_type="Positive Case",
        suite_type="Regression",
        automation_type="UI Automation",
        requirement_reference=requirement_reference,
        version=1,
        status="ACTIVE",
        source_document="coverage_integration_fsd.txt",
    )


def test_traceability_and_coverage_pipeline(
    tmp_path,
):
    """
    Phase 14.2 integration test.

    Validates:

        Requirement Repository
                ↓
        Test Case Repository
                ↓
        Traceability Service
                ↓
        Traceability Repository
                ↓
        Coverage Report

    Scenario:

        REQ001 -> TC001
        REQ002 -> TC002

        REQ003 remains uncovered.

    Expected coverage:

        Total      = 3
        Covered    = 2
        Uncovered  = 1
        Percentage = 66.67%
    """

    # ------------------------------------------------------------
    # 1. Isolated repositories
    # ------------------------------------------------------------

    requirement_repository = RequirementRepository(
        storage_path=str(
            tmp_path / "requirements.json"
        )
    )

    test_case_repository = TestCaseRepository(
        storage_path=str(
            tmp_path / "test_cases.json"
        )
    )

    traceability_repository = (
        TraceabilityRepository(
            storage_path=str(
                tmp_path / "traceability.json"
            )
        )
    )

    # ------------------------------------------------------------
    # 2. Requirements
    # ------------------------------------------------------------

    requirements = [
        build_requirement(
            "REQ001",
            "The system must allow a user to create a valid lead.",
        ),
        build_requirement(
            "REQ002",
            "The system must validate the mobile number.",
        ),
        build_requirement(
            "REQ003",
            "The system must display a lead confirmation message.",
        ),
    ]

    requirement_repository.save_many(
        requirements
    )

    stored_requirements = (
        requirement_repository.get_all()
    )

    assert len(stored_requirements) == 3

    stored_requirement_ids = {
        requirement.requirement_id
        for requirement in stored_requirements
    }

    assert stored_requirement_ids == {
        "REQ001",
        "REQ002",
        "REQ003",
    }

    # ------------------------------------------------------------
    # 3. Test Cases
    # ------------------------------------------------------------

    test_cases = [
        build_test_case(
            "TC001",
            "Create a valid lead",
            requirement_reference="REQ001",
        ),
        build_test_case(
            "TC002",
            "Validate mobile number",
            requirement_reference="REQ002",
        ),
        build_test_case(
            "TC003",
            "Unrelated test case",
        ),
    ]

    test_case_repository.save_many(
        test_cases
    )

    stored_test_cases = (
        test_case_repository.get_all()
    )

    assert len(stored_test_cases) == 3

    stored_test_case_ids = {
        test_case.test_case_id
        for test_case in stored_test_cases
    }

    assert stored_test_case_ids == {
        "TC001",
        "TC002",
        "TC003",
    }

    # ------------------------------------------------------------
    # 4. Traceability Service
    # ------------------------------------------------------------

    traceability_service = TraceabilityService(
        requirement_repository=requirement_repository,
        test_case_repository=test_case_repository,
        traceability_repository=(
            traceability_repository
        ),
    )

    # ------------------------------------------------------------
    # 5. Create mappings
    # ------------------------------------------------------------

    mapping_1 = (
        traceability_service.create_mapping(
            requirement_id="REQ001",
            test_case_id="TC001",
        )
    )

    assert mapping_1.requirement_id == "REQ001"
    assert mapping_1.test_case_id == "TC001"
    assert mapping_1.relationship_type == "COVERED"
    assert mapping_1.status == "ACTIVE"

    mapping_2 = (
        traceability_service.create_mapping(
            requirement_id="REQ002",
            test_case_id="TC002",
        )
    )

    assert mapping_2.requirement_id == "REQ002"
    assert mapping_2.test_case_id == "TC002"
    assert mapping_2.relationship_type == "COVERED"
    assert mapping_2.status == "ACTIVE"

    # ------------------------------------------------------------
    # 6. Traceability Repository
    # ------------------------------------------------------------

    stored_mappings = (
        traceability_repository.get_all()
    )

    assert len(stored_mappings) == 2

    mapping_pairs = {
        (
            mapping.requirement_id,
            mapping.test_case_id,
        )
        for mapping in stored_mappings
    }

    assert mapping_pairs == {
        ("REQ001", "TC001"),
        ("REQ002", "TC002"),
    }

    # ------------------------------------------------------------
    # 7. Coverage Report
    # ------------------------------------------------------------

    coverage_report = CoverageReport(
        traceability_service=traceability_service
    )

    coverage_summary = (
        coverage_report.generate_summary()
    )

    assert (
        coverage_summary["total_requirements"]
        == 3
    )

    assert (
        coverage_summary["covered_requirements"]
        == 2
    )

    assert (
        coverage_summary["uncovered_requirements"]
        == 1
    )

    assert (
        coverage_summary["coverage_percentage"]
        == 66.67
    )

    # ------------------------------------------------------------
    # 8. Covered requirements
    # ------------------------------------------------------------

    covered_requirements = (
        coverage_report
        .get_covered_requirements()
    )

    covered_ids = {
        requirement.requirement_id
        for requirement in covered_requirements
    }

    assert covered_ids == {
        "REQ001",
        "REQ002",
    }

    # ------------------------------------------------------------
    # 9. Uncovered requirements
    # ------------------------------------------------------------

    uncovered_requirements = (
        coverage_report
        .get_uncovered_requirements()
    )

    uncovered_ids = {
        requirement.requirement_id
        for requirement in uncovered_requirements
    }

    assert uncovered_ids == {
        "REQ003",
    }

    # ------------------------------------------------------------
    # 10. Unmapped test cases
    # ------------------------------------------------------------

    unmapped_test_cases = (
        coverage_report
        .get_unmapped_test_cases()
    )

    unmapped_ids = {
        test_case.test_case_id
        for test_case in unmapped_test_cases
    }

    assert unmapped_ids == {
        "TC003",
    }

    # ------------------------------------------------------------
    # 11. Requirement coverage matrix
    # ------------------------------------------------------------

    coverage_details = (
        coverage_report
        .get_requirement_coverage_details()
    )

    assert len(coverage_details) == 3

    details_by_requirement = {
        detail["requirement_id"]: detail
        for detail in coverage_details
    }

    assert (
        details_by_requirement["REQ001"]
        ["test_case_ids"]
        == ["TC001"]
    )

    assert (
        details_by_requirement["REQ002"]
        ["test_case_ids"]
        == ["TC002"]
    )

    assert (
        details_by_requirement["REQ003"]
        ["test_case_ids"]
        == []
    )

    assert (
        details_by_requirement["REQ001"]
        ["covered"]
        is True
    )

    assert (
        details_by_requirement["REQ002"]
        ["covered"]
        is True
    )

    assert (
        details_by_requirement["REQ003"]
        ["covered"]
        is False
    )

    # ------------------------------------------------------------
    # 12. Final repository assertions
    # ------------------------------------------------------------

    assert (
        requirement_repository.count()
        == 3
    )

    assert (
        test_case_repository.count()
        == 3
    )

    assert (
        traceability_repository.count()
        == 2
    )

    print(
        "Phase 14.2 traceability and coverage "
        "integration: PASS"
    )


def test_retired_latest_test_case_does_not_cover_requirement(tmp_path):
    requirement_repository = RequirementRepository(
        storage_path=str(tmp_path / "requirements_retired.json")
    )
    test_case_repository = TestCaseRepository(
        storage_path=str(tmp_path / "test_cases_retired.json")
    )
    traceability_repository = TraceabilityRepository(
        storage_path=str(tmp_path / "traceability_retired.json")
    )

    requirement_repository.save_many([
        build_requirement("REQ001", "A requirement covered only by a retired case."),
        build_requirement("REQ002", "A requirement covered by an active case."),
        build_requirement("REQ003", "An uncovered requirement."),
    ])

    retired_case_v1 = build_test_case(
        "TC001", "A test case later retired", requirement_reference="REQ001"
    )
    active_case = build_test_case(
        "TC002", "An active test case", requirement_reference="REQ002"
    )
    unmapped_case = build_test_case("TC003", "An active unmapped test case")
    test_case_repository.save_many([retired_case_v1, active_case, unmapped_case])
    test_case_repository.update(TestCase(
        test_case_id="TC001",
        module=retired_case_v1.module,
        scenario=retired_case_v1.scenario,
        test_steps=retired_case_v1.test_steps,
        expected_result=retired_case_v1.expected_result,
        priority=retired_case_v1.priority,
        test_type=retired_case_v1.test_type,
        suite_type=retired_case_v1.suite_type,
        automation_type=retired_case_v1.automation_type,
        pre_condition=retired_case_v1.pre_condition,
        requirement_reference="REQ001",
        version=2,
        status="RETIRED",
    ))
    traceability_repository.save_many([
        Traceability("REQ001", "TC001", status="ACTIVE"),
        Traceability("REQ002", "TC002", status="ACTIVE"),
    ])

    service = TraceabilityService(
        requirement_repository=requirement_repository,
        test_case_repository=test_case_repository,
        traceability_repository=traceability_repository,
    )

    assert service.calculate_coverage() == {
        "total_requirements": 3,
        "covered_requirements": 1,
        "uncovered_requirements": 2,
        "coverage_percentage": 33.33,
    }
    assert not service.is_requirement_covered("REQ001")
    assert service.is_requirement_covered("REQ002")
    assert service.get_test_cases_for_requirement("REQ001") == []
    assert service.get_requirements_for_test_case("TC001") == []
    assert {
        case.test_case_id for case in service.get_unmapped_test_cases()
    } == {"TC003"}

    matrix = {
        row["requirement_id"]: row
        for row in service.get_traceability_matrix()
    }
    assert matrix["REQ001"]["test_case_ids"] == []
    assert matrix["REQ001"]["covered"] is False
    assert matrix["REQ002"]["test_case_ids"] == ["TC002"]
