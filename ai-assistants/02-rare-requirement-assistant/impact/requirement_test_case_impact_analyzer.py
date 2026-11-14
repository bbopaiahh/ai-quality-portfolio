from dataclasses import dataclass
from typing import List, Optional

from models.requirement import Requirement
from models.test_case import TestCase
from traceability.traceability_service import TraceabilityService


IMPACTED = "IMPACTED"
NOT_IMPACTED = "NOT_IMPACTED"
REVIEW = "REVIEW"


@dataclass
class RequirementTestCaseImpact:
    """
    Represents the potential impact of a Requirement change
    on an existing Test Case.
    """

    requirement_id: str
    test_case_id: str
    impact_status: str
    reason: str
    previous_requirement_version: Optional[int] = None
    current_requirement_version: Optional[int] = None


class RequirementTestCaseImpactAnalyzer:
    """
    Analyze the impact of Requirement changes on existing
    Test Cases using active traceability relationships.

    This component is intentionally conservative.

    It does NOT:
        - modify Requirements
        - modify Test Cases
        - create Test Cases
        - retire Test Cases
        - modify traceability
        - decide final KEEP/MODIFY/RETIRE actions

    Its responsibility is only to identify Test Cases that are
    potentially affected by a changed Requirement.
    """

    def __init__(
        self,
        traceability_service: TraceabilityService | None = None,
    ):
        self.traceability_service = (
            traceability_service
            or TraceabilityService()
        )

    def analyze_requirement_change(
        self,
        previous_requirement: Requirement,
        current_requirement: Requirement,
    ) -> List[RequirementTestCaseImpact]:
        """
        Analyze the Test Cases affected by a Requirement change.

        The analyzer uses active Requirement -> Test Case
        traceability as the primary source of impact.

        Parameters:
            previous_requirement:
                Previous version of the Requirement.

            current_requirement:
                Current version of the Requirement.

        Returns:
            List of RequirementTestCaseImpact records.
        """

        self._validate_requirements(
            previous_requirement,
            current_requirement,
        )

        test_cases = (
            self.traceability_service
            .get_test_cases_for_requirement(
                current_requirement.requirement_id
            )
        )

        impacts: List[RequirementTestCaseImpact] = []

        for test_case in test_cases:
            impacts.append(
                RequirementTestCaseImpact(
                    requirement_id=(
                        current_requirement.requirement_id
                    ),
                    test_case_id=self._get_test_case_id(
                        test_case
                    ),
                    impact_status=IMPACTED,
                    reason=(
                        "Test Case is actively traceable to "
                        "the changed Requirement."
                    ),
                    previous_requirement_version=(
                        previous_requirement.version
                    ),
                    current_requirement_version=(
                        current_requirement.version
                    ),
                )
            )

        return impacts

    def analyze_changed_requirements(
        self,
        requirement_changes: List[
            tuple[Requirement, Requirement]
        ],
    ) -> List[RequirementTestCaseImpact]:
        """
        Analyze multiple Requirement changes.

        Each tuple contains:

            (
                previous_requirement,
                current_requirement
            )

        Returns a combined list of potential Test Case impacts.
        """

        if not requirement_changes:
            return []

        impacts: List[RequirementTestCaseImpact] = []

        for (
            previous_requirement,
            current_requirement,
        ) in requirement_changes:
            impacts.extend(
                self.analyze_requirement_change(
                    previous_requirement=previous_requirement,
                    current_requirement=current_requirement,
                )
            )

        return impacts

    def get_affected_test_cases(
        self,
        previous_requirement: Requirement,
        current_requirement: Requirement,
    ) -> List[TestCase]:
        """
        Return the actual Test Case objects affected by
        a Requirement change.
        """

        self._validate_requirements(
            previous_requirement,
            current_requirement,
        )

        return (
            self.traceability_service
            .get_test_cases_for_requirement(
                current_requirement.requirement_id
            )
        )

    def is_requirement_change_impacting_test_cases(
        self,
        previous_requirement: Requirement,
        current_requirement: Requirement,
    ) -> bool:
        """
        Return True when the changed Requirement has at least
        one actively traceable Test Case.
        """

        impacts = self.analyze_requirement_change(
            previous_requirement=previous_requirement,
            current_requirement=current_requirement,
        )

        return bool(impacts)

    @staticmethod
    def _validate_requirements(
        previous_requirement: Requirement,
        current_requirement: Requirement,
    ) -> None:
        """
        Validate the Requirement inputs.
        """

        if not isinstance(
            previous_requirement,
            Requirement,
        ):
            raise TypeError(
                "previous_requirement must be a Requirement instance."
            )

        if not isinstance(
            current_requirement,
            Requirement,
        ):
            raise TypeError(
                "current_requirement must be a Requirement instance."
            )

        if (
            previous_requirement.requirement_id
            != current_requirement.requirement_id
        ):
            raise ValueError(
                "Previous and current Requirements must have "
                "the same requirement_id."
            )

        if (
            current_requirement.version
            <= previous_requirement.version
        ):
            raise ValueError(
                "Current Requirement version must be greater "
                "than the previous Requirement version."
            )

    @staticmethod
    def _get_test_case_id(
        test_case: TestCase,
    ) -> str:
        """
        Return the Test Case identifier.

        Kept as a small helper so the analyzer depends only
        on the existing TestCase model contract.
        """

        test_case_id = getattr(
            test_case,
            "test_case_id",
            None,
        )

        if not test_case_id:
            raise ValueError(
                "Test Case does not contain a valid test_case_id."
            )

        return str(test_case_id)