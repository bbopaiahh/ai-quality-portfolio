"""
Quality Report

Converts the output of TestSuiteQualityAnalyzer into a clean,
structured quality report.

This module does not perform quality analysis itself.
It only organizes and summarizes the analyzer output.
"""

from typing import Dict, List, Any


class QualityReport:
    """
    Builds a structured quality report from TestSuiteQualityAnalyzer output.
    """

    def __init__(self, analysis_result: Dict[str, Any]):
        """
        Initialize the quality report.

        Args:
            analysis_result: Result returned by TestSuiteQualityAnalyzer.analyze()
        """

        if not isinstance(analysis_result, dict):
            raise TypeError("analysis_result must be a dictionary")

        self.analysis_result = analysis_result

    def generate_summary(self) -> Dict[str, Any]:
        """
        Return the overall quality summary.

        Coverage values are derived from the analyzer findings because
        the analyzer does not directly expose covered/uncovered
        requirement counts in its summary.
        """

        summary = self.analysis_result.get("summary", {})

        total_requirements = summary.get(
            "total_requirements",
            0,
        )

        critical_coverage_gaps = self.get_critical_coverage_gaps()

        uncovered_requirements = len(
            critical_coverage_gaps
        )

        covered_requirements = max(
            total_requirements - uncovered_requirements,
            0,
        )

        return {
            "quality_score": summary.get(
                "quality_score",
                0,
            ),
            "total_requirements": total_requirements,
            "covered_requirements": covered_requirements,
            "uncovered_requirements": uncovered_requirements,
            "total_test_cases": summary.get(
                "total_test_cases",
                0,
            ),
            "active_test_cases": summary.get(
                "active_test_cases",
                summary.get("total_test_cases", 0),
            ),
            "critical_gaps": summary.get(
                "critical_coverage_gaps",
                len(critical_coverage_gaps),
            ),
            "quality_concerns": summary.get(
                "quality_concerns",
                0,
            ),
            "duplicate_candidates": summary.get(
                "duplicate_candidates",
                len(self.get_duplicates()),
            ),
            "requirements_with_gaps": summary.get(
                "requirements_with_gaps",
                len(self.get_requirement_gaps()),
            ),
            "single_test_requirements": summary.get(
                "single_test_requirements",
                0,
            ),
        }

    def get_critical_coverage_gaps(self) -> List[Dict[str, Any]]:
        """
        Return critical requirement coverage gaps.
        """

        return self.analysis_result.get(
            "critical_coverage_gaps",
            [],
        )

    def get_quality_concerns(self) -> List[Dict[str, Any]]:
        """
        Return quality concerns identified by the analyzer.
        """

        return self.analysis_result.get(
            "quality_concerns",
            [],
        )

    def get_requirement_gaps(self) -> List[Dict[str, Any]]:
        """
        Return all requirement-level gaps.
        """

        return self.analysis_result.get(
            "requirement_gaps",
            [],
        )

    def get_duplicates(self) -> List[Any]:
        """
        Return duplicate test-case candidates.
        """

        return self.analysis_result.get(
            "duplicates",
            [],
        )

    def get_priority_analysis(self) -> Dict[str, Any]:
        """
        Return priority coverage analysis.
        """

        return self.analysis_result.get(
            "priority_analysis",
            {},
        )

    def get_automation_analysis(self) -> Dict[str, Any]:
        """
        Return automation coverage analysis.
        """

        return self.analysis_result.get(
            "automation_analysis",
            {},
        )

    def get_test_type_analysis(self) -> Dict[str, Any]:
        """
        Return test-type coverage analysis.
        """

        return self.analysis_result.get(
            "test_type_analysis",
            {},
        )

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate the complete structured quality report.
        """

        return {
            "summary": self.generate_summary(),
            "critical_coverage_gaps": self.get_critical_coverage_gaps(),
            "quality_concerns": self.get_quality_concerns(),
            "requirement_gaps": self.get_requirement_gaps(),
            "duplicates": self.get_duplicates(),
            "priority_analysis": self.get_priority_analysis(),
            "automation_analysis": self.get_automation_analysis(),
            "test_type_analysis": self.get_test_type_analysis(),
        }