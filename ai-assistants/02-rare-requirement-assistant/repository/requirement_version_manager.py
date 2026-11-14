from dataclasses import dataclass
from typing import List, Optional

from models.requirement import Requirement
from repository.requirement_repository import RequirementRepository


KEEP = "KEEP"
MODIFY = "MODIFY"
ADD = "ADD"
RETIRE = "RETIRE"
REVIEW = "REVIEW"


@dataclass
class RequirementChange:
    """
    Represents a detected change for a Requirement.

    This is intentionally independent of any particular change-detection
    implementation so that a future Requirement Change Detector can produce
    these objects without coupling the version manager to detection logic.
    """

    action: str
    requirement_id: Optional[str] = None
    new_requirement: Optional[Requirement] = None
    existing_requirement: Optional[Requirement] = None
    reason: str = ""


class RequirementVersionManager:
    """
    Applies detected requirement changes to the Requirement Repository
    while preserving Requirement IDs and version history.

    Supported actions:

        KEEP
            Existing requirement remains unchanged.

        MODIFY
            Existing Requirement ID is preserved.
            A new version is created.

        ADD
            A new globally unique Requirement ID is assigned.
            Version starts at 1.

        RETIRE
            Existing Requirement ID is preserved.
            A new RETIRED version is created.

        REVIEW
            Existing requirement remains unchanged.
            No repository version is created.
            Manual review is required.
    """

    def __init__(
        self,
        repository: Optional[RequirementRepository] = None,
    ):
        self.repository = repository or RequirementRepository()

    def apply_changes(
        self,
        changes: List[RequirementChange],
    ) -> List[Requirement]:
        """
        Apply detected changes to the requirement repository.

        Returns:
            The latest repository version of every affected requirement.
        """

        if not changes:
            return []

        affected_requirements: List[Requirement] = []

        for change in changes:
            self._validate_change(change)

            if change.action == KEEP:
                if change.existing_requirement:
                    affected_requirements.append(
                        change.existing_requirement
                    )

            elif change.action == MODIFY:
                updated_requirement = self._apply_modify(change)
                affected_requirements.append(updated_requirement)

            elif change.action == ADD:
                new_requirement = self._apply_add(change)
                affected_requirements.append(new_requirement)

            elif change.action == RETIRE:
                retired_requirement = self._apply_retire(change)
                affected_requirements.append(retired_requirement)

            elif change.action == REVIEW:
                # REVIEW is intentionally a safe no-op.
                # The change detector could not safely determine whether
                # the requirement should be changed or retired.
                # Leave the repository unchanged.
                continue

            else:
                raise ValueError(
                    f"Unsupported requirement change action: "
                    f"{change.action}"
                )

        return affected_requirements

    def _validate_change(
        self,
        change: RequirementChange,
    ) -> None:
        """Validate the basic contract for a requirement change."""

        if not isinstance(change, RequirementChange):
            raise TypeError(
                "changes must contain RequirementChange instances."
            )

        supported_actions = {
            KEEP,
            MODIFY,
            ADD,
            RETIRE,
            REVIEW,
        }

        if change.action not in supported_actions:
            raise ValueError(
                f"Unsupported requirement change action: "
                f"{change.action}"
            )

    def _apply_modify(
        self,
        change: RequirementChange,
    ) -> Requirement:
        """
        Create a new version of an existing requirement while preserving
        its Requirement ID.
        """

        existing_requirement = change.existing_requirement
        new_requirement = change.new_requirement

        if existing_requirement is None:
            raise ValueError(
                "MODIFY action requires an existing requirement."
            )

        if new_requirement is None:
            raise ValueError(
                "MODIFY action requires a new requirement."
            )

        updated_requirement = existing_requirement.create_new_version(
            module=new_requirement.module,
            requirement=new_requirement.requirement,
            requirement_type=new_requirement.requirement_type,
            priority=new_requirement.priority,
            source_document=(
                new_requirement.source_document
                or existing_requirement.source_document
            ),
            source_reference=(
                new_requirement.source_reference
                or existing_requirement.source_reference
            ),
            status="ACTIVE",
        )

        return self.repository.save_version(updated_requirement)

    def _apply_add(
        self,
        change: RequirementChange,
    ) -> Requirement:
        """
        Add a genuinely new requirement.

        A new globally unique Requirement ID is assigned.
        """

        new_requirement = change.new_requirement

        if new_requirement is None:
            raise ValueError(
                "ADD action requires a new requirement."
            )

        new_requirement_id = self._get_next_requirement_id()

        added_requirement = Requirement(
            requirement_id=new_requirement_id,
            module=new_requirement.module,
            requirement=new_requirement.requirement,
            requirement_type=new_requirement.requirement_type,
            priority=new_requirement.priority,
            source_document=new_requirement.source_document,
            source_reference=new_requirement.source_reference,
            version=1,
            status="ACTIVE",
        )

        return self.repository.save(added_requirement)

    def _apply_retire(
        self,
        change: RequirementChange,
    ) -> Requirement:
        """
        Create a new RETIRED version of an existing requirement while
        preserving its Requirement ID.
        """

        existing_requirement = change.existing_requirement

        if existing_requirement is None:
            raise ValueError(
                "RETIRE action requires an existing requirement."
            )

        retired_requirement = existing_requirement.retire()

        return self.repository.save_version(retired_requirement)

    def _get_next_requirement_id(
        self,
    ) -> str:
        """
        Find the next available global Requirement ID.

        Existing IDs are scanned so that IDs are never accidentally reused.
        """

        requirements = self.repository.get_all()

        highest_number = 0

        for requirement in requirements:
            requirement_id = requirement.requirement_id

            if not requirement_id.startswith("REQ"):
                continue

            numeric_part = requirement_id[3:]

            if not numeric_part.isdigit():
                continue

            number = int(numeric_part)
            highest_number = max(highest_number, number)

        return f"REQ{highest_number + 1:03d}"