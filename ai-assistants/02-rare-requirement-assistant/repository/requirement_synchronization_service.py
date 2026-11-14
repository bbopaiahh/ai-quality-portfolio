"""Safe orchestration for requirement detection and version management.

This service does not extract requirements or alter traceability. It coordinates
the existing detector, RequirementRepository, and RequirementVersionManager.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Set

from models.requirement import Requirement
from repository.requirement_change_detector import RequirementChangeDetector
from repository.requirement_version_manager import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    REVIEW,
    RequirementChange,
    RequirementVersionManager,
)
from repository.requirement_repository import RequirementRepository


@dataclass
class RequirementSynchronizationReport:
    """Outcome of one requirement synchronization attempt."""

    proposed_changes: List[RequirementChange] = field(default_factory=list)
    applied_changes: List[RequirementChange] = field(default_factory=list)
    review_required: List[RequirementChange] = field(default_factory=list)
    affected_requirements: List[Requirement] = field(default_factory=list)

    @property
    def counts(self):
        counts = {action: 0 for action in (KEEP, MODIFY, ADD, RETIRE, REVIEW)}
        for change in self.proposed_changes:
            counts[change.action] = counts.get(change.action, 0) + 1
        return counts


class RequirementSynchronizationService:
    """Detect changes and apply safe actions while preserving version history.

    REVIEW proposals are returned to the caller and are not persisted.
    Retirement is possible only when the caller explicitly supplies candidate
    IDs and confirms the extraction is complete; the detector enforces both.
    """

    def __init__(
        self,
        repository: Optional[RequirementRepository] = None,
        detector: Optional[RequirementChangeDetector] = None,
        version_manager: Optional[RequirementVersionManager] = None,
    ) -> None:
        self.repository = repository or RequirementRepository()
        self.detector = detector or RequirementChangeDetector()
        self.version_manager = version_manager or RequirementVersionManager(
            repository=self.repository
        )

        # Avoid accidentally applying changes to a different repository.
        manager_repository = getattr(self.version_manager, "repository", None)
        if manager_repository is not self.repository:
            raise ValueError(
                "RequirementSynchronizationService and RequirementVersionManager "
                "must use the same RequirementRepository instance."
            )

    def synchronize(
        self,
        extracted_requirements: List[Requirement],
        *,
        generation_complete: bool = False,
        retirement_candidates: Optional[Set[str]] = None,
    ) -> RequirementSynchronizationReport:
        """Compare one extraction with repository state and apply safe actions."""
        incoming = list(extracted_requirements or [])
        if not incoming:
            # An empty extraction is not evidence that all requirements vanished.
            return RequirementSynchronizationReport()

        existing = self.repository.get_all()
        changes = self.detector.detect_changes(
            new_requirements=incoming,
            existing_requirements=existing,
            generation_complete=generation_complete,
            retirement_candidates=retirement_candidates or set(),
        )

        report = RequirementSynchronizationReport(proposed_changes=changes)
        report.review_required = [
            change for change in changes if change.action == REVIEW
        ]

        # REVIEW is deliberately excluded from application; keep it visible to
        # the caller rather than allowing the version manager to silently skip it.
        safe_changes = [
            change for change in changes
            if change.action in {KEEP, MODIFY, ADD, RETIRE}
        ]
        report.applied_changes = safe_changes
        if safe_changes:
            report.affected_requirements = self.version_manager.apply_changes(
                safe_changes
            )
        return report
