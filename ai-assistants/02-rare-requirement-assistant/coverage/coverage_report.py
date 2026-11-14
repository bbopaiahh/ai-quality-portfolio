from typing import Dict, List

from models.requirement import Requirement
from models.test_case import TestCase
from traceability.traceability_service import (
    TraceabilityService,
)


class CoverageReport:
    """
    Generates requirement coverage reports using the
    TraceabilityService.

    The report focuses on active Requirements and their
    active Test Case mappings.
    """

    def __init__(
        self,
        traceability_service: TraceabilityService,
    ):
        self.traceability_service = (
            traceability_service
        )

    def generate_summary(self) -> Dict[str, float | int]:
        """
        Generate the overall requirement coverage summary.
        """

        return (
            self.traceability_service
            .calculate_coverage()
        )

    def get_covered_requirements(
        self,
    ) -> List[Requirement]:
        """
        Return all active Requirements that are covered
        by at least one active Test Case.
        """

        return (
            self.traceability_service
            .get_covered_requirements()
        )

    def get_uncovered_requirements(
        self,
    ) -> List[Requirement]:
        """
        Return all active Requirements that have no
        active Test Case mapping.
        """

        return (
            self.traceability_service
            .get_uncovered_requirements()
        )

    def get_unmapped_test_cases(
        self,
    ) -> List[TestCase]:
        """
        Return Test Cases that do not have an active
        Requirement mapping.
        """

        return (
            self.traceability_service
            .get_unmapped_test_cases()
        )

    def get_requirement_coverage_details(
        self,
    ) -> List[Dict[str, object]]:
        """
        Return detailed coverage information for every
        active Requirement.

        Each record contains:

        - Requirement ID
        - Module
        - Requirement
        - Test Case IDs
        - Covered status
        """

        return (
            self.traceability_service
            .get_traceability_matrix()
        )

    def generate_report(self) -> Dict[str, object]:
        """
        Generate a complete requirement coverage report.
        """

        summary = self.generate_summary()

        covered_requirements = (
            self.get_covered_requirements()
        )

        uncovered_requirements = (
            self.get_uncovered_requirements()
        )

        unmapped_test_cases = (
            self.get_unmapped_test_cases()
        )

        details = (
            self.get_requirement_coverage_details()
        )

        return {
            "summary": summary,
            "covered_requirements": [
                self._requirement_to_dict(
                    requirement
                )
                for requirement
                in covered_requirements
            ],
            "uncovered_requirements": [
                self._requirement_to_dict(
                    requirement
                )
                for requirement
                in uncovered_requirements
            ],
            "unmapped_test_cases": [
                self._test_case_to_dict(
                    test_case
                )
                for test_case
                in unmapped_test_cases
            ],
            "details": details,
        }

    def format_text_report(self) -> str:
        """
        Generate a human-readable text coverage report.
        """

        report = self.generate_report()

        summary = report["summary"]

        lines = [
            "Requirement Coverage Report",
            "=" * 50,
            "",
            (
                "Total Requirements      : "
                f"{summary['total_requirements']}"
            ),
            (
                "Covered Requirements    : "
                f"{summary['covered_requirements']}"
            ),
            (
                "Uncovered Requirements  : "
                f"{summary['uncovered_requirements']}"
            ),
            (
                "Coverage Percentage     : "
                f"{summary['coverage_percentage']:.2f}%"
            ),
            "",
            "Covered Requirements",
            "-" * 50,
        ]

        covered_requirements = (
            report["covered_requirements"]
        )

        if covered_requirements:
            for requirement in covered_requirements:
                lines.append(
                    self._format_requirement_line(
                        requirement
                    )
                )
        else:
            lines.append(
                "None"
            )

        lines.extend(
            [
                "",
                "Uncovered Requirements",
                "-" * 50,
            ]
        )

        uncovered_requirements = (
            report["uncovered_requirements"]
        )

        if uncovered_requirements:
            for requirement in uncovered_requirements:
                lines.append(
                    self._format_requirement_line(
                        requirement
                    )
                )
        else:
            lines.append(
                "None"
            )

        lines.extend(
            [
                "",
                "Unmapped Test Cases",
                "-" * 50,
            ]
        )

        unmapped_test_cases = (
            report["unmapped_test_cases"]
        )

        if unmapped_test_cases:
            for test_case in unmapped_test_cases:
                lines.append(
                    self._format_test_case_line(
                        test_case
                    )
                )
        else:
            lines.append(
                "None"
            )

        return "\n".join(lines)

    @staticmethod
    def _requirement_to_dict(
        requirement: Requirement,
    ) -> Dict[str, object]:
        """
        Convert a Requirement object into report data.
        """

        return {
            "requirement_id": (
                requirement.requirement_id
            ),
            "module": requirement.module,
            "requirement": requirement.requirement,
            "requirement_type": (
                requirement.requirement_type
            ),
            "priority": requirement.priority,
            "status": requirement.status,
        }

    @staticmethod
    def _test_case_to_dict(
        test_case: TestCase,
    ) -> Dict[str, object]:
        """
        Convert a TestCase object into report data.
        """

        return {
            "test_case_id": (
                test_case.test_case_id
            ),
            "module": test_case.module,
            "scenario": test_case.scenario,
            "priority": test_case.priority,
            "test_type": test_case.test_type,
            "suite_type": test_case.suite_type,
            "automation_type": (
                test_case.automation_type
            ),
        }

    @staticmethod
    def _format_requirement_line(
        requirement: Dict[str, object],
    ) -> str:
        """
        Format one Requirement for the text report.
        """

        return (
            f"{requirement['requirement_id']} | "
            f"{requirement['module']} | "
            f"{requirement['requirement']}"
        )

    @staticmethod
    def _format_test_case_line(
        test_case: Dict[str, object],
    ) -> str:
        """
        Format one Test Case for the text report.
        """

        return (
            f"{test_case['test_case_id']} | "
            f"{test_case['module']} | "
            f"{test_case['scenario']}"
        )