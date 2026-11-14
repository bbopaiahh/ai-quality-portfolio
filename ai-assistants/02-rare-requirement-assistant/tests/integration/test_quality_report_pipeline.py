from models.test_case import TestCase
from models.traceability import Traceability
from models.requirement import Requirement
from quality.test_suite_quality_analyzer import TestSuiteQualityAnalyzer
from quality.quality_report import QualityReport


def build_requirement(
    requirement_id,
    requirement,
    priority="P1",
):
    """
    Build a Requirement using the project's existing model.
    """

    return Requirement(
        requirement_id=requirement_id,
        module="Lead Management",
        requirement=requirement,
        requirement_type="Functional",
        priority=priority,
    )


def build_test_case(
    test_case_id,
    requirement_reference,
    scenario,
    expected_result,
    priority="P1",
    test_type="Positive Case",
    automation_type="UI Automation",
):
    return TestCase(
        test_case_id=test_case_id,
        module="Lead Management",
        scenario=scenario,
        test_steps="Execute the required test steps",
        expected_result=expected_result,
        priority=priority,
        test_type=test_type,
        suite_type="Regression",
        automation_type=automation_type,
        requirement_reference=requirement_reference,
    )


def build_mapping(
    requirement_id,
    test_case_id,
):
    return Traceability(
        requirement_id=requirement_id,
        test_case_id=test_case_id,
        relationship_type="COVERED",
        status="ACTIVE",
    )


def test_quality_report_pipeline():
    """
    Phase 14.4 integration test.

    Validates:

        Requirements
            +
        Test Cases
            +
        Traceability
            ↓
        Quality Analyzer
            ↓
        Quality Report
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
            expected_result="Lead is created successfully.",
            priority="P0",
            test_type="Positive Case",
            automation_type="UI Automation",
        ),
        build_test_case(
            test_case_id="TC002",
            requirement_reference="REQ001",
            scenario="Create a valid lead",
            expected_result="Lead is created successfully.",
            priority="P0",
            test_type="Positive Case",
            automation_type="UI Automation",
        ),
        build_test_case(
            test_case_id="TC003",
            requirement_reference="REQ001",
            scenario="Reject an invalid lead",
            expected_result="Invalid lead is rejected.",
            priority="P1",
            test_type="Negative Case",
            automation_type="UI Automation",
        ),
        build_test_case(
            test_case_id="TC004",
            requirement_reference="REQ002",
            scenario="Search leads within the required response time",
            expected_result="Search results are displayed under 1.8 seconds.",
            priority="P1",
            test_type="Positive Case",
            automation_type="UI Automation",
        ),
    ]

    assert len(test_cases) == 4

    # ------------------------------------------------------------
    # 3. Traceability
    # ------------------------------------------------------------

    mappings = [
        build_mapping("REQ001", "TC001"),
        build_mapping("REQ001", "TC002"),
        build_mapping("REQ001", "TC003"),
        build_mapping("REQ002", "TC004"),
    ]

    assert len(mappings) == 4

    # REQ003 deliberately has no mapping.

    # ------------------------------------------------------------
    # 4. Quality Analyzer
    # ------------------------------------------------------------

    analyzer = TestSuiteQualityAnalyzer()

    analysis_result = analyzer.analyze(
        requirements=requirements,
        test_cases=test_cases,
        mappings=mappings,
    )

    assert isinstance(analysis_result, dict)

    # ------------------------------------------------------------
    # 5. Quality Report
    # ------------------------------------------------------------

    report = QualityReport(analysis_result)

    summary = report.generate_summary()

    # ------------------------------------------------------------
    # 6. Summary validation
    # ------------------------------------------------------------

    assert summary["total_requirements"] == 3
    assert summary["covered_requirements"] == 2
    assert summary["uncovered_requirements"] == 1
    assert summary["total_test_cases"] == 4

    assert summary["critical_gaps"] == 1
    assert summary["quality_concerns"] >= 1
    assert summary["duplicate_candidates"] >= 1

    assert 0 <= summary["quality_score"] <= 100

    # ------------------------------------------------------------
    # 7. Critical coverage gaps
    # ------------------------------------------------------------

    critical_gaps = report.get_critical_coverage_gaps()

    assert len(critical_gaps) == 1
    assert critical_gaps[0]["requirement_id"] == "REQ003"

    # ------------------------------------------------------------
    # 8. Quality concerns
    # ------------------------------------------------------------

    concerns = report.get_quality_concerns()

    assert len(concerns) >= 1

    # ------------------------------------------------------------
    # 9. Duplicate analysis
    # ------------------------------------------------------------

    duplicates = report.get_duplicates()

    assert len(duplicates) >= 1

    duplicate_pair = duplicates[0]

    assert duplicate_pair.first_test_case_id == "TC001"
    assert duplicate_pair.second_test_case_id == "TC002"

    # ------------------------------------------------------------
    # 10. Priority analysis
    # ------------------------------------------------------------

    priority_analysis = report.get_priority_analysis()

    assert "P0" in priority_analysis
    assert priority_analysis["P0"]["covered_by_p0_p1"] == 1

    # ------------------------------------------------------------
    # 11. Automation analysis
    # ------------------------------------------------------------

    automation_analysis = report.get_automation_analysis()

    assert automation_analysis["total_test_cases"] == 4
    assert automation_analysis["automated_test_cases"] == 4

    # ------------------------------------------------------------
    # 12. Test type analysis
    # ------------------------------------------------------------

    test_type_analysis = report.get_test_type_analysis()

    assert test_type_analysis["total_test_cases"] == 4
    assert test_type_analysis["counts"]["Positive Case"] == 3
    assert test_type_analysis["counts"]["Negative Case"] == 1

    # ------------------------------------------------------------
    # 13. Complete report
    # ------------------------------------------------------------

    complete_report = report.generate_report()

    assert "summary" in complete_report
    assert "critical_coverage_gaps" in complete_report
    assert "quality_concerns" in complete_report
    assert "requirement_gaps" in complete_report
    assert "duplicates" in complete_report
    assert "priority_analysis" in complete_report
    assert "automation_analysis" in complete_report
    assert "test_type_analysis" in complete_report