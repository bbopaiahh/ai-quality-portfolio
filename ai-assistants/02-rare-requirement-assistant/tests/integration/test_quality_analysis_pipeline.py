from __future__ import annotations

from models.requirement import Requirement
from models.test_case import TestCase
from models.traceability import Traceability
from quality.test_suite_quality_analyzer import (
    TestSuiteQualityAnalyzer,
)


def build_requirement(
    requirement_id: str,
    requirement: str,
    priority: str = "P1",
) -> Requirement:
    """
    Build a deterministic Requirement for quality analysis.
    """

    return Requirement(
        requirement_id=requirement_id,
        module="Lead Management",
        requirement=requirement,
        requirement_type="Business Rule",
        priority=priority,
        source_document="quality_integration_fsd.txt",
        source_reference=requirement_id,
        status="ACTIVE",
        version=1,
    )


def build_test_case(
    test_case_id: str,
    requirement_reference: str,
    scenario: str,
    expected_result: str,
    priority: str = "P1",
    test_type: str = "Positive Case",
    automation_type: str = "UI Automation",
) -> TestCase:
    """
    Build a deterministic TestCase for quality analysis.
    """

    return TestCase(
        test_case_id=test_case_id,
        module="Lead Management",
        scenario=scenario,
        test_steps=(
            "Open the Lead Management screen.<br>"
            "Execute the scenario.<br>"
            "Verify the result."
        ),
        expected_result=expected_result,
        priority=priority,
        test_type=test_type,
        suite_type="Regression",
        automation_type=automation_type,
        requirement_reference=requirement_reference,
        version=1,
        status="ACTIVE",
        source_document="quality_integration_fsd.txt",
    )


def build_mapping(
    requirement_id: str,
    test_case_id: str,
) -> Traceability:
    """
    Build an active Requirement -> Test Case mapping.
    """

    return Traceability(
        requirement_id=requirement_id,
        test_case_id=test_case_id,
        relationship_type="COVERED",
        status="ACTIVE",
    )


def test_quality_analysis_pipeline():
    """
    Phase 14.3 integration test.

    Validates the complete quality-analysis input chain:

        Requirements
            +
        Test Cases
            +
        Traceability
            ↓
        Quality Analyzer
            ↓
        Quality Score
        Coverage Findings
        Risk Findings
        Priority Analysis
        Automation Analysis
        Test Type Analysis
        Duplicate Analysis

    Test design:

        REQ001
            Covered by positive + negative tests.

        REQ002
            Performance requirement.
            Covered by UI automation only, so the analyzer
            should identify a performance-specific concern.

        REQ003
            Completely uncovered.
            Should produce a CRITICAL finding.

        TC001 / TC002
            Intentionally very similar to exercise duplicate
            detection.
    """

    # ------------------------------------------------------------
    # 1. Requirements
    # ------------------------------------------------------------

    requirements = [
        build_requirement(
            "REQ001",
            "The system must allow a user to create a valid lead.",
            priority="P0",
        ),
        build_requirement(
            "REQ002",
            "Lead search results must load under 1.8 seconds "
            "for a database of 1M records.",
            priority="P1",
        ),
        build_requirement(
            "REQ003",
            "The system must encrypt all PII at rest using AES-256.",
            priority="P1",
        ),
    ]

    assert len(requirements) == 3

    # ------------------------------------------------------------
    # 2. Test Cases
    # ------------------------------------------------------------

    test_cases = [
        build_test_case(
            test_case_id="TC001",
            requirement_reference="REQ001",
            scenario="Create a valid lead",
            expected_result=(
                "Lead is created successfully."
            ),
            priority="P0",
            test_type="Positive Case",
            automation_type="UI Automation",
        ),
        build_test_case(
            test_case_id="TC002",
            requirement_reference="REQ001",
            scenario="Create a valid lead",
            expected_result=(
                "Lead is created successfully."
            ),
            priority="P0",
            test_type="Positive Case",
            automation_type="UI Automation",
        ),
        build_test_case(
            test_case_id="TC003",
            requirement_reference="REQ001",
            scenario="Reject an invalid lead",
            expected_result=(
                "Invalid lead is rejected."
            ),
            priority="P1",
            test_type="Negative Case",
            automation_type="UI Automation",
        ),
        build_test_case(
            test_case_id="TC004",
            requirement_reference="REQ002",
            scenario="Search leads within the required response time",
            expected_result=(
                "Search results are displayed under 1.8 seconds."
            ),
            priority="P1",
            test_type="Positive Case",
            automation_type="UI Automation",
        ),
    ]

    assert len(test_cases) == 4

    # ------------------------------------------------------------
    # 3. Traceability mappings
    # ------------------------------------------------------------

    mappings = [
        build_mapping(
            "REQ001",
            "TC001",
        ),
        build_mapping(
            "REQ001",
            "TC002",
        ),
        build_mapping(
            "REQ001",
            "TC003",
        ),
        build_mapping(
            "REQ002",
            "TC004",
        ),
    ]

    assert len(mappings) == 4

    # REQ003 deliberately has no mapping.

    # ------------------------------------------------------------
    # 4. Quality Analyzer
    # ------------------------------------------------------------

    analyzer = TestSuiteQualityAnalyzer()

    result = analyzer.analyze(
        requirements=requirements,
        test_cases=test_cases,
        mappings=mappings,
    )

    assert isinstance(result, dict)

    # ------------------------------------------------------------
    # 5. Result structure
    # ------------------------------------------------------------

    assert "summary" in result
    assert "requirement_gaps" in result
    assert "duplicates" in result
    assert "critical_coverage_gaps" in result
    assert "quality_concerns" in result
    assert "priority_analysis" in result
    assert "automation_analysis" in result
    assert "test_type_analysis" in result

    summary = result["summary"]

    assert isinstance(summary, dict)

    # ------------------------------------------------------------
    # 6. Basic suite statistics
    # ------------------------------------------------------------

    assert summary["total_requirements"] == 3
    assert summary["total_test_cases"] == 4

    # ------------------------------------------------------------
    # 7. Requirement gap analysis
    # ------------------------------------------------------------

    requirement_gaps = result["requirement_gaps"]

    assert isinstance(
        requirement_gaps,
        list,
    )

    gap_by_requirement = {
        gap["requirement_id"]: gap
        for gap in requirement_gaps
    }

    # REQ003 is completely uncovered.
    assert "REQ003" in gap_by_requirement

    assert (
        gap_by_requirement["REQ003"]["severity"]
        == "CRITICAL"
    )

    # REQ002 is covered, but performance testing is
    # represented only through UI automation.
    assert "REQ002" in gap_by_requirement

    assert (
        gap_by_requirement["REQ002"]["severity"]
        == "CONCERN"
    )

    # REQ001 has positive and negative coverage.
    # It should not be marked as a critical coverage gap.
    if "REQ001" in gap_by_requirement:
        assert (
            gap_by_requirement["REQ001"]["severity"]
            != "CRITICAL"
        )

    # ------------------------------------------------------------
    # 8. Critical vs concern summary
    # ------------------------------------------------------------

    assert (
        summary["critical_coverage_gaps"]
        == 1
    )

    assert (
        summary["quality_concerns"]
        >= 1
    )

    assert (
        summary["requirements_requiring_review"]
        >= 2
    )

    # ------------------------------------------------------------
    # 9. Duplicate detection
    # ------------------------------------------------------------

    duplicate_candidates = (
        result["duplicates"]
    )

    assert isinstance(
        duplicate_candidates,
        list,
    )

    duplicate_pairs = {
        (
            candidate.first_test_case_id,
            candidate.second_test_case_id,
        )
        for candidate in duplicate_candidates
    }

    assert (
        ("TC001", "TC002") in duplicate_pairs
        or ("TC002", "TC001") in duplicate_pairs
    )

    assert (
        summary["duplicate_candidates"]
        >= 1
    )

    # ------------------------------------------------------------
    # 10. Priority analysis
    # ------------------------------------------------------------

    priority_analysis = (
        result["priority_analysis"]
    )

    assert isinstance(
        priority_analysis,
        dict,
    )

    assert "P0" in priority_analysis
    assert "P1" in priority_analysis

    # P0 requirement REQ001 has P0 coverage.
    p0_analysis = priority_analysis["P0"]

    assert (
        p0_analysis["total"]
        == 1
    )

    assert (
        p0_analysis["covered_by_p0_p1"]
        == 1
    )

    # ------------------------------------------------------------
    # 11. Automation analysis
    # ------------------------------------------------------------

    automation_analysis = (
        result["automation_analysis"]
    )

    assert isinstance(
        automation_analysis,
        dict,
    )

    assert (
        automation_analysis["total_test_cases"]
        == 4
    )

    assert (
        automation_analysis["automated_test_cases"]
        == 4
    )

    assert (
        automation_analysis["automation_percentage"]
        == 100.0
    )

    # ------------------------------------------------------------
    # 12. Test type analysis
    # ------------------------------------------------------------

    test_type_analysis = (
        result["test_type_analysis"]
    )

    assert isinstance(
        test_type_analysis,
        dict,
    )

    assert "counts" in test_type_analysis
    assert "percentages" in test_type_analysis
    assert "total_test_cases" in test_type_analysis

    test_type_counts = test_type_analysis["counts"]

    assert (
            test_type_counts["Positive Case"]
            == 3
    )

    assert (
            test_type_counts["Negative Case"]
            == 1
    )

    assert (
            test_type_analysis["total_test_cases"]
            == 4
    )

    # ------------------------------------------------------------
    # 13. Quality score
    # ------------------------------------------------------------

    quality_score = summary["quality_score"]

    assert isinstance(
        quality_score,
        (int, float),
    )

    assert 0 <= quality_score <= 100

    # Because the suite contains an uncovered requirement,
    # the score should not represent a perfect suite.
    assert quality_score < 100

    # ------------------------------------------------------------
    # 14. Final consistency checks
    # ------------------------------------------------------------

    assert (
        summary["requirements_with_gaps"]
        == len(requirement_gaps)
    )

    assert (
        summary["requirements_requiring_review"]
        == len(requirement_gaps)
    )

    print(
        "Phase 14.3 quality analysis "
        "integration: PASS"
    )