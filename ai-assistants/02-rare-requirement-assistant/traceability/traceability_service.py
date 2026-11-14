from typing import Dict, List, Set

from models.requirement import Requirement
from models.test_case import TestCase
from models.traceability import Traceability

from repository.requirement_repository import (
    RequirementRepository,
)
from repository.test_case_repository import (
    TestCaseRepository,
)
from repository.traceability_repository import (
    TraceabilityRepository,
)


class TraceabilityService:
    """
    Service layer responsible for Requirement ↔ Test Case
    traceability and requirement coverage analysis.

    The service connects:

        RequirementRepository
                ↓
        TraceabilityRepository
                ↓
        TestCaseRepository

    It does not directly manage JSON persistence.
    """

    def __init__(
        self,
        requirement_repository: RequirementRepository | None = None,
        test_case_repository: TestCaseRepository | None = None,
        traceability_repository: (
            TraceabilityRepository | None
        ) = None,
    ):
        self.requirement_repository = (
            requirement_repository
            or RequirementRepository()
        )

        self.test_case_repository = (
            test_case_repository
            or TestCaseRepository()
        )

        self.traceability_repository = (
            traceability_repository
            or TraceabilityRepository()
        )

    def create_mapping(
        self,
        requirement_id: str,
        test_case_id: str,
        relationship_type: str = "COVERED",
    ) -> Traceability:
        """
        Create a Requirement → Test Case mapping.

        Both the Requirement and Test Case must exist.
        """

        self._validate_requirement(
            requirement_id
        )

        self._validate_test_case(
            test_case_id
        )

        traceability = Traceability(
            requirement_id=requirement_id,
            test_case_id=test_case_id,
            relationship_type=relationship_type,
            status="ACTIVE",
        )

        return self.traceability_repository.save(
            traceability
        )

    def create_mappings(
        self,
        requirement_id: str,
        test_case_ids: List[str],
        relationship_type: str = "COVERED",
    ) -> List[Traceability]:
        """
        Create multiple Test Case mappings for one
        Requirement.
        """

        if not test_case_ids:
            return []

        self._validate_requirement(
            requirement_id
        )

        traceabilities = []

        for test_case_id in test_case_ids:
            self._validate_test_case(
                test_case_id
            )

            traceabilities.append(
                Traceability(
                    requirement_id=requirement_id,
                    test_case_id=test_case_id,
                    relationship_type=relationship_type,
                    status="ACTIVE",
                )
            )

        return self.traceability_repository.save_many(
            traceabilities
        )

    def get_requirement_mappings(
        self,
        requirement_id: str,
    ) -> List[Traceability]:
        """
        Return all traceability mappings for a Requirement.
        """

        return (
            self.traceability_repository
            .get_by_requirement(requirement_id)
        )

    def get_test_case_mappings(
        self,
        test_case_id: str,
    ) -> List[Traceability]:
        """
        Return all traceability mappings for a Test Case.
        """

        return (
            self.traceability_repository
            .get_by_test_case(test_case_id)
        )

    def get_test_cases_for_requirement(
        self,
        requirement_id: str,
    ) -> List[TestCase]:
        """
        Return the actual Test Case objects mapped to
        a Requirement.
        """

        mappings = self.get_requirement_mappings(
            requirement_id
        )

        active_test_cases = self._get_active_test_cases_by_id()
        test_cases = []

        for mapping in mappings:

            if mapping.status != "ACTIVE":
                continue

            test_case = active_test_cases.get(mapping.test_case_id)

            if test_case is not None:
                test_cases.append(test_case)

        return test_cases

    def get_requirements_for_test_case(
        self,
        test_case_id: str,
    ) -> List[Requirement]:
        """
        Return the actual Requirement objects mapped to
        a Test Case.
        """

        mappings = self.get_test_case_mappings(
            test_case_id
        )

        if test_case_id not in self._get_active_test_cases_by_id():
            return []

        requirements = []

        for mapping in mappings:

            if mapping.status != "ACTIVE":
                continue

            requirement = (
                self.requirement_repository
                .get_by_id(mapping.requirement_id)
            )

            if requirement is not None:
                requirements.append(requirement)

        return requirements

    def is_requirement_covered(
        self,
        requirement_id: str,
    ) -> bool:
        """
        Return True when a Requirement has at least one
        active Test Case mapping.
        """

        active_test_case_ids = self._get_active_test_cases_by_id()
        mappings = self.get_requirement_mappings(
            requirement_id
        )

        return any(
            mapping.status == "ACTIVE"
            and mapping.test_case_id in active_test_case_ids
            for mapping in mappings
        )

    def get_uncovered_requirements(
        self,
    ) -> List[Requirement]:
        """
        Return all active Requirements that have no active
        Test Case mapping.
        """

        requirements = (
            self.requirement_repository
            .get_all()
        )

        return [
            requirement
            for requirement in requirements
            if (
                requirement.status == "ACTIVE"
                and not self.is_requirement_covered(
                    requirement.requirement_id
                )
            )
        ]

    def get_covered_requirements(
        self,
    ) -> List[Requirement]:
        """
        Return all active Requirements that have at least
        one active Test Case mapping.
        """

        requirements = (
            self.requirement_repository
            .get_all()
        )

        return [
            requirement
            for requirement in requirements
            if (
                requirement.status == "ACTIVE"
                and self.is_requirement_covered(
                    requirement.requirement_id
                )
            )
        ]

    def get_unmapped_test_cases(
        self,
    ) -> List[TestCase]:
        """
        Return Test Cases that have no active Requirement
        mapping.
        """

        test_cases = list(self._get_active_test_cases_by_id().values())

        active_test_case_ids = {
            test_case.test_case_id
            for test_case in test_cases
        }

        mapped_test_case_ids: Set[str] = {
            mapping.test_case_id
            for mapping in (
                self.traceability_repository
                .get_all()
            )
            if (
                mapping.status == "ACTIVE"
                and mapping.test_case_id in active_test_case_ids
            )
        }

        return [
            test_case
            for test_case in test_cases
            if (
                test_case.test_case_id
                not in mapped_test_case_ids
            )
        ]

    def calculate_coverage(
        self,
    ) -> Dict[str, float | int]:
        """
        Calculate requirement coverage.

        Coverage is calculated using active Requirements only.

        Formula:

            covered requirements
            -------------------- × 100
            total active requirements
        """

        requirements = (
            self.requirement_repository
            .get_all()
        )

        active_requirements = [
            requirement
            for requirement in requirements
            if requirement.status == "ACTIVE"
        ]

        total_requirements = len(
            active_requirements
        )

        covered_requirements = sum(
            1
            for requirement in active_requirements
            if self.is_requirement_covered(
                requirement.requirement_id
            )
        )

        uncovered_requirements = (
            total_requirements
            - covered_requirements
        )

        if total_requirements == 0:
            coverage_percentage = 0.0
        else:
            coverage_percentage = (
                covered_requirements
                / total_requirements
            ) * 100

        return {
            "total_requirements": total_requirements,
            "covered_requirements": covered_requirements,
            "uncovered_requirements": uncovered_requirements,
            "coverage_percentage": round(
                coverage_percentage,
                2,
            ),
        }

    def get_traceability_matrix(
        self,
    ) -> List[Dict[str, object]]:
        """
        Build a simple Requirement → Test Case
        traceability matrix.

        Each row represents one active Requirement.
        """

        requirements = (
            self.requirement_repository
            .get_all()
        )

        matrix = []

        for requirement in requirements:

            if requirement.status != "ACTIVE":
                continue

            mappings = (
                self.get_requirement_mappings(
                    requirement.requirement_id
                )
            )

            eligible_test_case_ids = self._get_active_test_cases_by_id()
            active_test_case_ids = [
                mapping.test_case_id
                for mapping in mappings
                if (
                    mapping.status == "ACTIVE"
                    and mapping.test_case_id in eligible_test_case_ids
                )
            ]

            matrix.append(
                {
                    "requirement_id": (
                        requirement.requirement_id
                    ),
                    "module": requirement.module,
                    "requirement": (
                        requirement.requirement
                    ),
                    "test_case_ids": (
                        active_test_case_ids
                    ),
                    "covered": bool(
                        active_test_case_ids
                    ),
                }
            )

        return matrix

    def _get_active_test_cases_by_id(self) -> Dict[str, TestCase]:
        """Return latest ACTIVE test cases keyed by stable Test Case ID."""
        return {
            test_case.test_case_id: test_case
            for test_case in self.test_case_repository.get_all()
            if (getattr(test_case, "status", "ACTIVE") or "ACTIVE")
            .strip()
            .upper() == "ACTIVE"
        }

    def deactivate_mapping(
        self,
        requirement_id: str,
        test_case_id: str,
    ) -> Traceability:
        """
        Mark an existing mapping as inactive.
        """

        mapping = (
            self.traceability_repository
            .get_mapping(
                requirement_id,
                test_case_id,
            )
        )

        if mapping is None:
            raise ValueError(
                "Traceability mapping not found: "
                f"{requirement_id} -> "
                f"{test_case_id}"
            )

        updated_mapping = mapping.deactivate()

        return self.traceability_repository.update(
            updated_mapping
        )

    def activate_mapping(
        self,
        requirement_id: str,
        test_case_id: str,
    ) -> Traceability:
        """
        Mark an existing mapping as active.
        """

        mapping = (
            self.traceability_repository
            .get_mapping(
                requirement_id,
                test_case_id,
            )
        )

        if mapping is None:
            raise ValueError(
                "Traceability mapping not found: "
                f"{requirement_id} -> "
                f"{test_case_id}"
            )

        updated_mapping = mapping.activate()

        return self.traceability_repository.update(
            updated_mapping
        )

    def _validate_requirement(
        self,
        requirement_id: str,
    ) -> Requirement:
        """
        Validate that a Requirement exists.
        """

        requirement = (
            self.requirement_repository
            .get_by_id(requirement_id)
        )

        if requirement is None:
            raise ValueError(
                "Requirement not found: "
                f"{requirement_id}"
            )

        return requirement

    def _validate_test_case(
        self,
        test_case_id: str,
    ) -> TestCase:
        """
        Validate that a Test Case exists.
        """

        test_case = (
            self.test_case_repository
            .get_by_id(test_case_id)
        )

        if test_case is None:
            raise ValueError(
                "Test Case not found: "
                f"{test_case_id}"
            )

        return test_case
