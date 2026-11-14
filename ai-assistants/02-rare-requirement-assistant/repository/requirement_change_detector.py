"""Conservative, domain-agnostic requirement change detection for RARE.

This component detects likely requirement changes; it does not persist changes.
Persistence and version creation remain the responsibility of
RequirementVersionManager.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Sequence, Set, Tuple

from models.requirement import Requirement
from repository.requirement_version_manager import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    REVIEW,
    RequirementChange,
)


class RequirementChangeDetector:
    """Compare extracted requirements with the latest repository versions.

    Safety rules:
    - Extractor-generated IDs are not treated as stable identity.
    - Exact text/module matches are preferred.
    - A clear, unique near-match may be classified as MODIFY.
    - Ambiguous matches are sent to REVIEW.
    - An unmatched existing requirement is REVIEW by default.
    - RETIRE requires both a complete extraction and an explicit retirement
      candidate supplied by a separate, trusted decision process.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.82,
        minimum_match_margin: float = 0.10,
    ) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1.")
        if not 0.0 <= minimum_match_margin <= 1.0:
            raise ValueError("minimum_match_margin must be between 0 and 1.")

        self.similarity_threshold = similarity_threshold
        self.minimum_match_margin = minimum_match_margin

    def detect_changes(
        self,
        new_requirements: Sequence[Requirement],
        existing_requirements: Sequence[Requirement],
        *,
        generation_complete: bool = False,
        retirement_candidates: Optional[Set[str]] = None,
    ) -> List[RequirementChange]:
        """Return proposed actions without modifying either input collection."""
        incoming = list(new_requirements or [])
        existing = list(existing_requirements or [])
        candidates_for_retirement = set(retirement_candidates or set())

        self._validate_requirements(incoming, "new_requirements")
        self._validate_requirements(existing, "existing_requirements")

        # Repository input is expected to contain one latest version per ID.
        # If duplicate IDs are passed, refuse to make unsafe identity choices.
        duplicate_existing_ids = self._duplicate_ids(existing)
        used_existing_ids: Set[str] = set()
        results: List[RequirementChange] = []
        ambiguous_incoming_indexes: Set[int] = set()

        # Duplicate extraction lines must not turn into duplicate repository
        # requirements. Mark every occurrence for review before matching.
        incoming_signatures: Dict[Tuple[str, str], List[int]] = {}
        for index, requirement in enumerate(incoming):
            signature = (
                self._normalize(requirement.module),
                self._normalize(requirement.requirement),
            )
            incoming_signatures.setdefault(signature, []).append(index)

        for signature_indexes in incoming_signatures.values():
            if len(signature_indexes) > 1:
                for index in signature_indexes:
                    results.append(self._change(
                        REVIEW, incoming[index], None,
                        "The new extraction contains duplicate requirement wording in the same module; manual review is required.",
                    ))
                    ambiguous_incoming_indexes.add(index)

        # Pass 1: exact requirement text + module matches. Do not rely on
        # extractor-generated IDs because they restart at REQ001 per document.
        for incoming_index, candidate in enumerate(incoming):
            possible = [
                item for item in existing
                if item.requirement_id not in used_existing_ids
                and self._same_text_and_module(candidate, item)
            ]

            if len(possible) > 1 or any(
                item.requirement_id in duplicate_existing_ids for item in possible
            ):
                results.append(self._change(
                    REVIEW, candidate, None,
                    "Multiple existing requirements match the same module and text; manual identity review is required.",
                ))
                ambiguous_incoming_indexes.add(incoming_index)
                continue

            if len(possible) == 1:
                matched = possible[0]
                if self._is_retired(matched):
                    results.append(self._change(
                        REVIEW, candidate, matched,
                        "The matching repository requirement is retired; confirm whether it should be reactivated.",
                    ))
                elif self._metadata_changed(candidate, matched):
                    results.append(self._change(
                        MODIFY, candidate, matched,
                        "Requirement wording and module are unchanged, but extracted requirement metadata differs.",
                    ))
                else:
                    results.append(self._change(
                        KEEP, candidate, matched,
                        "Requirement wording and module match the existing requirement.",
                    ))
                used_existing_ids.add(matched.requirement_id)
                ambiguous_incoming_indexes.add(incoming_index)

        # Pass 2: match remaining incoming requirements to unique high-confidence
        # near-matches. Similarity is only used as evidence, never as proof when
        # two candidates are close or the source context conflicts.
        for incoming_index, candidate in enumerate(incoming):
            if incoming_index in ambiguous_incoming_indexes:
                continue

            scored: List[Tuple[float, Requirement]] = []
            for item in existing:
                if item.requirement_id in used_existing_ids:
                    continue
                if self._is_retired(item):
                    continue
                score = self._match_score(candidate, item)
                if score >= self.similarity_threshold:
                    scored.append((score, item))

            scored.sort(key=lambda pair: pair[0], reverse=True)
            if scored:
                best_score, best_match = scored[0]
                second_score = scored[1][0] if len(scored) > 1 else 0.0

                if best_score - second_score < self.minimum_match_margin:
                    results.append(self._change(
                        REVIEW, candidate, None,
                        "More than one existing requirement is a plausible match; manual identity review is required.",
                    ))
                else:
                    results.append(self._change(
                        MODIFY, candidate, best_match,
                        f"A unique likely match was found (similarity {best_score:.2f}); review the proposed wording change.",
                    ))
                    used_existing_ids.add(best_match.requirement_id)
            else:
                results.append(self._change(
                    ADD, candidate, None,
                    "No sufficiently similar active requirement was found in the repository.",
                ))

        # Pass 3: any repository item not matched to an incoming requirement is
        # never retired merely because it was absent from this extraction.
        for item in existing:
            if item.requirement_id in used_existing_ids:
                continue

            if item.requirement_id in duplicate_existing_ids:
                action = REVIEW
                reason = "Duplicate repository Requirement IDs were supplied; retirement is blocked pending review."
            elif (
                generation_complete
                and item.requirement_id in candidates_for_retirement
                and not self._is_retired(item)
            ):
                action = RETIRE
                reason = "Requirement is an explicit retirement candidate and the source extraction was marked complete."
            else:
                action = REVIEW
                if not generation_complete:
                    reason = "Requirement was absent from an extraction not confirmed complete; retirement is unsafe."
                elif item.requirement_id not in candidates_for_retirement:
                    reason = "Requirement was absent from the new extraction but was not explicitly approved as a retirement candidate."
                else:
                    reason = "Requirement is already retired or its state needs review; no automatic retirement was applied."

            results.append(RequirementChange(
                action=action,
                requirement_id=item.requirement_id,
                existing_requirement=item,
                reason=reason,
            ))

        return results

    @staticmethod
    def _validate_requirements(
        requirements: Sequence[Requirement],
        parameter_name: str,
    ) -> None:
        for index, requirement in enumerate(requirements):
            if not isinstance(requirement, Requirement):
                raise TypeError(
                    f"{parameter_name}[{index}] must be a Requirement instance."
                )
            if not requirement.requirement_id:
                raise ValueError(
                    f"{parameter_name}[{index}] has no requirement_id."
                )

    @staticmethod
    def _duplicate_ids(requirements: Sequence[Requirement]) -> Set[str]:
        seen: Set[str] = set()
        duplicates: Set[str] = set()
        for requirement in requirements:
            if requirement.requirement_id in seen:
                duplicates.add(requirement.requirement_id)
            seen.add(requirement.requirement_id)
        return duplicates

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        text = (value or "").casefold()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return " ".join(text.split())

    def _same_text_and_module(
        self,
        first: Requirement,
        second: Requirement,
    ) -> bool:
        return (
            self._normalize(first.requirement) == self._normalize(second.requirement)
            and self._normalize(first.module) == self._normalize(second.module)
        )

    def _match_score(
        self,
        incoming: Requirement,
        existing: Requirement,
    ) -> float:
        incoming_text = self._normalize(incoming.requirement)
        existing_text = self._normalize(existing.requirement)
        if not incoming_text or not existing_text:
            return 0.0

        text_score = SequenceMatcher(None, incoming_text, existing_text).ratio()
        incoming_module = self._normalize(incoming.module)
        existing_module = self._normalize(existing.module)

        if incoming_module == existing_module:
            return text_score

        # A module move is possible, but requires stronger textual evidence.
        if text_score >= 0.92:
            return text_score - 0.02
        return 0.0

    @staticmethod
    def _metadata_changed(
        incoming: Requirement,
        existing: Requirement,
    ) -> bool:
        return (
            incoming.requirement_type != existing.requirement_type
            or incoming.priority != existing.priority
        )

    @staticmethod
    def _is_retired(requirement: Requirement) -> bool:
        return (requirement.status or "").strip().upper() == "RETIRED"

    @staticmethod
    def _change(
        action: str,
        incoming: Requirement,
        existing: Optional[Requirement],
        reason: str,
    ) -> RequirementChange:
        return RequirementChange(
            action=action,
            requirement_id=(existing.requirement_id if existing else None),
            new_requirement=incoming,
            existing_requirement=existing,
            reason=reason,
        )
