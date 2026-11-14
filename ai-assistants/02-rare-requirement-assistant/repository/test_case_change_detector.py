from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


# Backward-compatible module-level change constants.
KEEP = "KEEP"
MODIFY = "MODIFY"
ADD = "ADD"
RETIRE = "RETIRE"
REVIEW = "REVIEW"


@dataclass(init=False)
class ChangeRecord:
    """One detected change between the repository and generated suite."""

    change_type: str
    test_case_id: str
    test_case: Any = None
    existing_test_case: Any = None
    reason: str = ""

    def __init__(
        self,
        change_type: Optional[str] = None,
        test_case_id: str = "",
        test_case: Any = None,
        existing_test_case: Any = None,
        reason: str = "",
        *,
        action: Optional[str] = None,
        new_test_case: Any = None,
    ) -> None:
        if change_type is not None and action is not None and change_type != action:
            raise ValueError("change_type and action must contain the same value.")

        resolved_change_type = change_type if change_type is not None else action
        if resolved_change_type is None:
            raise TypeError("ChangeRecord requires 'change_type' or 'action'.")

        if test_case is not None and new_test_case is not None:
            if test_case is not new_test_case and test_case != new_test_case:
                raise ValueError(
                    "test_case and new_test_case must refer to the same test case."
                )

        self.change_type = resolved_change_type
        self.test_case_id = test_case_id
        self.test_case = test_case if test_case is not None else new_test_case
        self.existing_test_case = existing_test_case
        self.reason = reason

    @property
    def action(self) -> str:
        return self.change_type

    @property
    def new_test_case(self) -> Any:
        return self.test_case


class TestCaseChange(ChangeRecord):
    """Legacy compatibility wrapper used by older RARE callers."""

    def __init__(
        self,
        action: Optional[str] = None,
        test_case_id: str = "",
        new_test_case: Any = None,
        existing_test_case: Any = None,
        reason: str = "",
        *,
        change_type: Optional[str] = None,
        test_case: Any = None,
    ) -> None:
        super().__init__(
            change_type=change_type,
            action=action,
            test_case_id=test_case_id,
            test_case=test_case,
            new_test_case=new_test_case,
            existing_test_case=existing_test_case,
            reason=reason,
        )


class TestCaseChangeDetector:
    """
    Domain-agnostic KEEP / MODIFY / ADD / RETIRE detector.

    The detector contains only generic matching mechanics and does not
    depend on hard-coded business-domain vocabulary.

    Identity is derived from the supplied test cases using this order:

        1. Requirement reference
        2. Module + scenario exact identity
        3. Generic structured-rule fingerprint
        4. Generic semantic identity
        5. Conservative fuzzy identity
        6. ADD / RETIRE

    Test Case IDs are deliberately excluded from identity because generated
    IDs can change between runs and can restart for independent document
    chunks.
    """

    KEEP = KEEP
    MODIFY = MODIFY
    ADD = ADD
    RETIRE = RETIRE
    REVIEW = REVIEW

    SEMANTIC_MATCH_THRESHOLD = 0.72
    FUZZY_MATCH_THRESHOLD = 0.72
    FUZZY_SCENARIO_THRESHOLD = 0.70
    FUZZY_MARGIN = 0.08
    # The score is normalized only over fields that contain evidence. This
    # threshold preserves matches with shared states and numeric rules while
    # rejecting pairs that agree only on generic words and polarity.
    COVERAGE_THRESHOLD = 0.65

    # Retirement is destructive, so it is allowed only when the generated
    # suite appears sufficiently complete relative to the repository.
    RETIREMENT_COMPLETENESS_RATIO = 0.50

    # Kept as an empty compatibility attribute. Domain terminology must not
    # be encoded in the detector; vocabulary is learned from each case.
    SYNONYM_GROUPS: Dict[str, Set[str]] = {}
    WORKFLOW_STATES: Set[str] = set()

    STOPWORDS: Set[str] = {
        "the", "a", "an", "and", "or", "to", "of", "for", "with",
        "when", "where", "that", "this", "from", "into", "after", "before",
        "then", "is", "are", "be", "by", "on", "in", "as", "at", "does",
        "not", "verify", "system", "should", "ensure", "test", "case",
        "behavior", "successful", "successfully", "validate", "validation",
        "check", "checks", "checked", "perform", "performed", "using",
        "must", "shall", "will", "can", "may", "page", "user", "application",
    }

    API_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
    HTTP_STATUS_PATTERN = r"\b(?:HTTP\s*)?(\d{3})\b"

    _FIELDS_FOR_CONTENT = (
        "module", "scenario", "pre_condition", "test_steps",
        "expected_result", "priority", "test_type", "suite_type",
        "automation_type",
    )

    def detect_changes(
        self,
        new_test_cases: Sequence[Any],
        existing_test_cases: Sequence[Any],
        generation_complete: bool = False,
        retirement_candidates: Optional[Set[str]] = None,
    ) -> List[ChangeRecord]:
        new_cases = list(new_test_cases or [])
        existing_cases = list(existing_test_cases or [])
        changes: List[ChangeRecord] = []
        matched_existing: Set[int] = set()

        for new_case in new_cases:
            match_index, match_reason = self._find_match(
                new_case, existing_cases, matched_existing
            )

            if self._requires_clarification(new_case):
                if match_index is not None and match_reason not in {
                    "ambiguous fuzzy identity",
                    "conflicting fuzzy identity",
                }:
                    matched_existing.add(match_index)
                changes.append(
                    ChangeRecord(
                        change_type=self.REVIEW,
                        test_case_id=self._display_id(new_case),
                        test_case=new_case,
                        existing_test_case=(
                            existing_cases[match_index]
                            if match_index is not None
                            else None
                        ),
                        reason=(
                            "The generated expected result says the behavior "
                            "needs clarification. No repository change was "
                            "applied; manual review is required."
                        ),
                    )
                )
                continue

            if match_reason in {
                "ambiguous fuzzy identity",
                "conflicting fuzzy identity",
                "related structured rule identity",
            }:
                if match_index is not None:
                    matched_existing.add(match_index)
                changes.append(
                    ChangeRecord(
                        change_type=self.REVIEW,
                        test_case_id=self._display_id(new_case),
                        test_case=new_case,
                        existing_test_case=existing_cases[match_index],
                        reason=self._fuzzy_review_reason(match_reason),
                    )
                )
                continue

            if match_index is None:
                changes.append(
                    ChangeRecord(
                        change_type=self.ADD,
                        test_case_id=self._display_id(new_case),
                        test_case=new_case,
                        reason="Test case does not exist in the repository.",
                    )
                )
                continue

            matched_existing.add(match_index)
            existing_case = existing_cases[match_index]

            if self._field(existing_case, "status", "ACTIVE") != "ACTIVE":
                changes.append(
                    ChangeRecord(
                        change_type=self.REVIEW,
                        test_case_id=self._display_id(existing_case),
                        test_case=new_case,
                        existing_test_case=existing_case,
                        reason=(
                            "The matching repository case is retired. "
                            "Automatic reactivation is blocked; review is "
                            "required before creating a new version."
                        ),
                    )
                )
                continue

            if self._content_equal(new_case, existing_case):
                changes.append(
                    ChangeRecord(
                        change_type=self.KEEP,
                        test_case_id=self._display_id(existing_case),
                        test_case=new_case,
                        existing_test_case=existing_case,
                        reason=(
                            "No test case content changes detected. "
                            f"Identity matched using {match_reason}."
                        ),
                    )
                )
            else:
                changes.append(
                    ChangeRecord(
                        change_type=self.MODIFY,
                        test_case_id=self._display_id(existing_case),
                        test_case=new_case,
                        existing_test_case=existing_case,
                        reason=(
                            "Test case content has changed. "
                            f"Identity matched using {match_reason}."
                        ),
                    )
                )

        unmatched_existing = [
            (index, existing_case)
            for index, existing_case in enumerate(existing_cases)
            if index not in matched_existing
        ]

        # Missing from one generated run is NOT proof that an existing
        # repository test case is obsolete. Retirement therefore requires
        # BOTH: (1) a complete generation and (2) an explicit retirement
        # candidate supplied by a higher-level impact-analysis layer.
        # Until that layer exists, unmatched cases are always REVIEW.
        retirement_candidates = {
            str(test_case_id).strip()
            for test_case_id in (retirement_candidates or set())
            if str(test_case_id).strip()
        }
        retirement_allowed = bool(generation_complete) and self._retirement_is_safe(
            new_case_count=len(new_cases),
            existing_case_count=len(existing_cases),
            unmatched_count=len(unmatched_existing),
        )

        for index, existing_case in unmatched_existing:
            existing_id = self._display_id(existing_case)
            if retirement_allowed and existing_id in retirement_candidates:
                change_type = self.RETIRE
                reason = (
                    "Existing test case is no longer present in the newly "
                    "generated test suite, and generation completeness "
                    "supports retirement."
                )
            else:
                change_type = self.REVIEW
                reason = (
                    "Existing test case is not present in the newly generated "
                    "suite, but generation completeness is insufficient to "
                    "safely retire it. Manual review is required."
                )

            changes.append(
                ChangeRecord(
                    change_type=change_type,
                    test_case_id=self._display_id(existing_case),
                    test_case=None,
                    existing_test_case=existing_case,
                    reason=reason,
                )
            )

        return changes

    def _retirement_is_safe(
        self,
        *,
        new_case_count: int,
        existing_case_count: int,
        unmatched_count: int,
    ) -> bool:
        """Apply the legacy completeness heuristic for explicit callers.

        This method does not establish business obsolescence. It only checks
        whether a generated suite is large enough for retirement to even be
        considered. The public detector still requires ``generation_complete``
        to be explicitly True.
        """
        if unmatched_count == 0:
            return True

        if existing_case_count <= 0 or new_case_count <= 0:
            return False

        completeness_ratio = new_case_count / existing_case_count

        if completeness_ratio < self.RETIREMENT_COMPLETENESS_RATIO:
            return False

        if unmatched_count > new_case_count:
            return False

        return True

    def summarize(self, changes: Sequence[ChangeRecord]) -> Dict[str, int]:
        summary = {KEEP: 0, MODIFY: 0, ADD: 0, RETIRE: 0, REVIEW: 0}
        for change in changes or []:
            if isinstance(change, dict):
                change_type = change.get("change_type", change.get("action"))
            else:
                change_type = getattr(
                    change, "change_type", getattr(change, "action", None)
                )
            if change_type in summary:
                summary[change_type] += 1
        return summary

    def detect(
        self,
        new_test_cases: Sequence[Any],
        existing_test_cases: Sequence[Any],
        generation_complete: bool = False,
        retirement_candidates: Optional[Set[str]] = None,
    ) -> List[ChangeRecord]:
        """Backward-compatible public entry point.

        ``generation_complete`` defaults to False so legacy callers cannot
        accidentally trigger destructive retirement.
        """
        return self.detect_changes(
            new_test_cases=new_test_cases,
            existing_test_cases=existing_test_cases,
            generation_complete=generation_complete,
            retirement_candidates=retirement_candidates,
        )

    # ------------------------------------------------------------------
    # Match orchestration
    # ------------------------------------------------------------------

    def _find_match(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Tuple[Optional[int], str]:
        # Prefer a matching active case over a historical retired version.
        # The latter must never be silently reactivated by MODIFY.
        active_indexes = [
            index
            for index, case in enumerate(existing_cases)
            if self._field(case, "status", "ACTIVE") == "ACTIVE"
            and index not in matched_existing
        ]
        if active_indexes:
            active_cases = [existing_cases[index] for index in active_indexes]
            active_match, active_reason = self._find_match_in_pool(
                new_case, active_cases, set()
            )
            if active_match is not None:
                return active_indexes[active_match], active_reason

        return self._find_match_in_pool(
            new_case, existing_cases, matched_existing
        )

    def _find_match_in_pool(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Tuple[Optional[int], str]:
        new_requirement = self._normalized_requirement_reference(new_case)
        if new_requirement:
            candidates = [
                i for i, case in enumerate(existing_cases)
                if i not in matched_existing
                and self._normalized_requirement_reference(case) == new_requirement
            ]
            if len(candidates) == 1:
                return candidates[0], "requirement reference"
            if len(candidates) > 1:
                best = self._best_candidate_by_secondary_identity(
                    new_case, candidates, existing_cases
                )
                if best is not None:
                    return best, "requirement reference"

        exact_candidates = [
            i for i, case in enumerate(existing_cases)
            if i not in matched_existing and self._exact_identity(new_case, case)
        ]
        if len(exact_candidates) == 1:
            return exact_candidates[0], "exact identity"
        if len(exact_candidates) > 1:
            best = self._best_candidate_by_secondary_identity(
                new_case, exact_candidates, existing_cases
            )
            if best is not None:
                return best, "exact identity"

        coverage_match = self._match_by_business_coverage_identity(
            new_case, existing_cases, matched_existing
        )
        if coverage_match is not None:
            return coverage_match, "generic coverage identity"

        rule_match = self._match_by_business_rule_fingerprint(
            new_case, existing_cases, matched_existing
        )
        if rule_match is not None:
            return rule_match, "generic business-rule fingerprint"

        semantic_match = self._match_by_semantic_identity(
            new_case, existing_cases, matched_existing
        )
        if semantic_match is not None:
            return semantic_match, "semantic identity"

        fuzzy_match = self._match_by_fuzzy_identity(
            new_case, existing_cases, matched_existing
        )
        if fuzzy_match is not None:
            return fuzzy_match, "fuzzy identity"

        strong_scenario_match = self._match_by_strong_scenario_identity(
            new_case, existing_cases, matched_existing
        )
        if strong_scenario_match is not None:
            return strong_scenario_match, "strong scenario identity"

        related_rule_match = self._match_by_related_rule_context(
            new_case, existing_cases, matched_existing
        )
        if related_rule_match is not None:
            return related_rule_match, "related structured rule identity"

        ambiguous_match = self._find_ambiguous_fuzzy_candidate(
            new_case, existing_cases, matched_existing
        )
        if ambiguous_match is not None:
            return ambiguous_match, "ambiguous fuzzy identity"

        conflicting_match = self._find_conflicting_fuzzy_candidate(
            new_case, existing_cases, matched_existing
        )
        if conflicting_match is not None:
            return conflicting_match, "conflicting fuzzy identity"

        return None, ""

    @staticmethod
    def _requires_clarification(test_case: Any) -> bool:
        expected_result = str(
            TestCaseChangeDetector._field(test_case, "expected_result", "")
            or ""
        ).casefold()
        return any(
            phrase in expected_result
            for phrase in (
                "requires clarification",
                "needs clarification",
                "not explicitly specified",
            )
        )

    @staticmethod
    def _fuzzy_review_reason(reason: str) -> str:
        if reason == "conflicting fuzzy identity":
            return (
                "A similar existing test case has a conflicting structured "
                "rule. No repository change was applied; manual review is required."
            )
        if reason == "related structured rule identity":
            return (
                "A generated case shares a measurable condition or state transition "
                "with an existing case, but their scope is not clearly identical. "
                "No repository change was applied; manual review is required."
            )
        return (
            "Multiple existing test cases are plausible matches. "
            "No repository change was applied; manual review is required."
        )

    def _match_by_strong_scenario_identity(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        """Match near-identical scenarios when metadata wording differs.

        The match requires a high scenario-text score, compatible polarity, and
        no detected structured-rule conflict. Ambiguous top candidates are left
        unmatched for review.
        """
        candidates: list[tuple[float, int]] = []
        scenario_competitors: list[tuple[float, int]] = []
        new_scenario = self._normalize_text(self._field(new_case, "scenario"))
        new_text = self._normalize_rule_text(self._case_text(new_case))
        for index, existing_case in enumerate(existing_cases):
            if index in matched_existing:
                continue
            scenario_score = self._similarity(
                new_scenario,
                self._normalize_text(self._field(existing_case, "scenario")),
            )
            if scenario_score < self.FUZZY_SCENARIO_THRESHOLD:
                continue
            scenario_competitors.append((scenario_score, index))
            if scenario_score < 0.82:
                continue
            old_text = self._normalize_rule_text(self._case_text(existing_case))
            if self._business_rules_conflict(new_case, existing_case):
                continue
            new_polarity = self._coverage_polarity(new_text)
            old_polarity = self._coverage_polarity(old_text)
            if new_polarity != old_polarity:
                continue
            score = (
                scenario_score * 0.70
                + self._token_similarity(
                    self._case_text(new_case), self._case_text(existing_case)
                ) * 0.20
                + self._numeric_similarity(
                    self._case_text(new_case), self._case_text(existing_case)
                ) * 0.10
            )
            candidates.append((score, index))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        scenario_competitors.sort(key=lambda item: item[0], reverse=True)
        if len(scenario_competitors) > 1:
            return None
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < self.FUZZY_MARGIN:
            return None
        return candidates[0][1]

    def _match_by_related_rule_context(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        """Find a unique near-match sharing both a transition target and limit.

        This is intentionally a REVIEW match: shared generic signals can establish
        a relationship without proving that two cases have identical scope.
        """
        candidates: list[tuple[float, int]] = []
        new_fingerprints = self._business_rule_fingerprints(new_case)
        new_targets = self._transition_targets(new_fingerprints)
        new_limits = self._numeric_value_units(new_fingerprints)
        new_text = self._case_text(new_case)
        new_polarity = self._coverage_polarity(
            self._normalize_rule_text(new_text)
        )
        for index, existing_case in enumerate(existing_cases):
            if index in matched_existing or self._business_rules_conflict(
                new_case, existing_case
            ):
                continue
            old_fingerprints = self._business_rule_fingerprints(existing_case)
            shared_targets = new_targets.intersection(
                self._transition_targets(old_fingerprints)
            )
            shared_limits = new_limits.intersection(
                self._numeric_value_units(old_fingerprints)
            )
            old_text = self._case_text(existing_case)
            if not shared_targets or not shared_limits:
                continue
            old_polarity = self._coverage_polarity(
                self._normalize_rule_text(old_text)
            )
            if {new_polarity, old_polarity} == {"NEGATIVE", "POSITIVE"}:
                continue
            scenario_score = self._similarity(
                self._normalize_text(self._field(new_case, "scenario")),
                self._normalize_text(self._field(existing_case, "scenario")),
            )
            token_score = self._token_similarity(new_text, old_text)
            if scenario_score < 0.45 or token_score < 0.40:
                continue
            score = scenario_score * 0.55 + token_score * 0.30 + self._numeric_similarity(
                new_text, old_text
            ) * 0.15
            candidates.append((score, index))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < self.FUZZY_MARGIN:
            return None
        return candidates[0][1]

    @staticmethod
    def _transition_targets(fingerprints: Set[str]) -> Set[str]:
        return {
            parts[3]
            for fingerprint in fingerprints
            if len(parts := fingerprint.split("|")) == 4
            and parts[0] == "TRANSITION"
            and parts[2] == "TO"
        }

    @staticmethod
    def _numeric_value_units(fingerprints: Set[str]) -> Set[Tuple[str, str]]:
        return {
            (parts[3], parts[4])
            for fingerprint in fingerprints
            if len(parts := fingerprint.split("|")) == 5
            and parts[0] == "VALUE"
        }

    # ------------------------------------------------------------------
    # Generic coverage / fingerprint matching
    # ------------------------------------------------------------------

    def _match_by_business_coverage_identity(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        new_identity = self._business_coverage_identity(new_case)
        if not new_identity:
            return None

        candidates: List[Tuple[float, int]] = []
        for index, existing_case in enumerate(existing_cases):
            if index in matched_existing:
                continue
            if self._business_rules_conflict(new_case, existing_case):
                continue

            old_identity = self._business_coverage_identity(existing_case)
            if not old_identity:
                continue

            score = self._coverage_similarity(new_identity, old_identity)
            if score >= self.COVERAGE_THRESHOLD:
                candidates.append((score, index))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.05:
            return None
        return candidates[0][1]

    def _business_coverage_identity(self, test_case: Any) -> Optional[Tuple[str, ...]]:
        text = self._normalize_rule_text(self._case_text(test_case))
        if not text:
            return None

        fingerprints = self._business_rule_fingerprints(test_case)
        concepts = self._coverage_concepts(text)
        polarity = self._coverage_polarity(text)
        states = tuple(sorted(self._extract_states(text)))
        api_signals = tuple(sorted(self._extract_api_signals(text)))
        numeric = tuple(sorted(self._extract_numeric_constraints(text)))

        if not fingerprints and not concepts and not states and not api_signals:
            return None

        return (
            "|".join(sorted(fingerprints)),
            "|".join(sorted(concepts)),
            polarity,
            "|".join(states),
            "|".join(api_signals),
            "|".join(numeric),
        )

    def _coverage_concepts(self, text: str) -> Set[str]:
        # Generic domain concepts are simply meaningful normalized tokens.
        # No business vocabulary is embedded here.
        tokens = self._semantic_tokens(text)
        return {token for token in tokens if len(token) >= 4}

    def _coverage_polarity(self, text: str) -> str:
        edge = {"exactly", "boundary", "edge", "just above", "just below"}
        negative = {
            "invalid", "failure", "fails", "failed", "rejected", "reject",
            "missing", "mismatch", "denied", "blocked", "blocks", "prevents",
            "does not", "not satisfy", "error",
        }
        positive = {
            "successfully", "accepted", "passes", "passed", "created",
            "updated", "approved", "allowed", "moves to", "transitions to",
        }
        if self._contains_any(text, edge):
            return "EDGE"
        if self._contains_any(text, negative):
            return "NEGATIVE"
        if self._contains_any(text, positive):
            return "POSITIVE"
        return "NEUTRAL"

    @staticmethod
    def _coverage_similarity(left: Tuple[str, ...], right: Tuple[str, ...]) -> float:
        if len(left) != len(right):
            return 0.0
        weights = (0.35, 0.20, 0.10, 0.10, 0.15, 0.10)
        score = 0.0
        informative_weight = 0.0
        for weight, l_value, r_value in zip(weights, left, right):
            # Missing structured signals are absence of evidence, not a
            # positive identity match. Counting empty fingerprints, state
            # lists, or numeric fields as equal made unrelated cases with
            # the same broad polarity appear highly similar.
            if not l_value and not r_value:
                continue

            informative_weight += weight
            if l_value == r_value:
                score += weight
                continue
            l_set = set(filter(None, l_value.split("|")))
            r_set = set(filter(None, r_value.split("|")))
            if l_set and r_set:
                score += weight * (len(l_set & r_set) / len(l_set | r_set))
        if informative_weight == 0.0:
            return 0.0
        return score / informative_weight

    def _business_rule_fingerprints(self, test_case: Any) -> Set[str]:
        """
        Extract domain-neutral structured rules from the case text.

        Fingerprints describe mechanics such as numeric constraints, API
        calls, HTTP outcomes, retries, explicit transitions and durations.
        The actual business nouns come from the supplied document/test case.
        """
        text = self._normalize_rule_text(self._case_text(test_case))
        fingerprints: Set[str] = set()
        fingerprints.update(self._extract_numeric_constraints(text))

        api = self._extract_api_fingerprint(text)
        if api:
            fingerprints.add(api)

        transition = self._extract_transition_fingerprint(text)
        if transition:
            fingerprints.add(transition)

        performance = self._extract_performance_fingerprint(text)
        if performance:
            fingerprints.add(performance)

        retry_count = self._extract_retry_count(text)
        if retry_count is not None and self._contains_any(
            text, {"retry", "retries", "retrying", "again"}
        ):
            fingerprints.add(f"RETRY|COUNT|{retry_count}")

        return fingerprints

    def _extract_numeric_constraints(self, text: str) -> Set[str]:
        """Capture explicit numeric constraints without knowing their domain."""
        result: Set[str] = set()
        number = r"\d+(?:\.\d+)?"
        normalized = self._normalize_rule_text(text)

        patterns = [
            rf"(?P<concept>[a-z][a-z0-9_]*(?:\s+[a-z][a-z0-9_]*){{0,4}})\s*"
            rf"(?P<op>>=|<=|>|<|=|equal to|equals|exactly|greater than|more than|above|over|less than|below|under)\s*"
            rf"(?P<value>{number})\s*(?P<unit>%|seconds?|minutes?|hours?|days?|records?|items?|users?|requests?)?",
            rf"(?P<concept>[a-z][a-z0-9_]*(?:\s+[a-z][a-z0-9_]*){{0,4}})\s+"
            rf"(?P<value>{number})\s*(?P<unit>%|seconds?|minutes?|hours?|days?|records?|items?|users?|requests?)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
                concept = self._clean_concept(match.group("concept"))
                value = self._normalize_number(match.group("value"))
                unit = (match.groupdict().get("unit") or "").casefold()
                if not concept or value is None:
                    continue

                op = match.groupdict().get("op")
                if op:
                    operator = self._canonical_operator(op)
                else:
                    operator = "EXACT"

                # Do not fingerprint a sentence-level number when the
                # captured concept is only a generic test-step verb.
                if concept in {"step", "steps", "case", "test", "page", "http"}:
                    continue

                result.add(
                    f"VALUE|{concept}|{operator}|{value}|{unit or 'UNSPECIFIED'}"
                )

        # Explicit ranges: "between 10 and 20" / "10-20" near a concept.
        range_pattern = (
            rf"(?P<concept>[a-z][a-z0-9_]*(?:\s+[a-z][a-z0-9_]*){{0,4}})\s+"
            rf"(?:between\s+)?(?P<low>{number})\s*(?:and|-|to)\s*(?P<high>{number})"
        )
        for match in re.finditer(range_pattern, normalized, flags=re.IGNORECASE):
            concept = self._clean_concept(match.group("concept"))
            low = self._normalize_number(match.group("low"))
            high = self._normalize_number(match.group("high"))
            if concept and low is not None and high is not None:
                result.add(f"RANGE|{concept}|{low}|{high}")

        return result

    def _extract_api_fingerprint(self, text: str) -> Optional[str]:
        endpoint_match = re.search(r"(?P<endpoint>/[A-Za-z0-9_\-./{}]+)", text)
        if not endpoint_match:
            return None
        endpoint = endpoint_match.group("endpoint").rstrip(".,;:")
        if not endpoint.startswith("/"):
            return None

        # Require API-like context; this remains generic and does not assume
        # a particular endpoint prefix beyond a slash path.
        has_api_context = bool(
            re.search(r"\b(?:api|endpoint|request|response|http)\b", text)
        )
        if not has_api_context:
            return None

        method = self._extract_api_method(text) or "METHOD_UNSPECIFIED"
        status = self._extract_http_status(text) or "HTTP_UNSPECIFIED"
        retry = "RETRY" if self._contains_any(
            text, {"retry", "retries", "retrying"}
        ) else "NO_RETRY"
        return f"API|{method}|{endpoint}|{status}|{retry}"

    def _extract_performance_fingerprint(self, text: str) -> Optional[str]:
        if not self._contains_any(
            text,
            {"performance", "response time", "latency", "within", "under", "load"},
        ):
            return None

        duration = re.search(
            r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|milliseconds?|ms|minutes?|mins?)",
            text,
            flags=re.IGNORECASE,
        )
        if not duration:
            return None
        value = self._normalize_number(duration.group(1))
        if value is None:
            return None
        return f"PERFORMANCE|DURATION|{value}|{duration.group(2).casefold()}"

    def _extract_transition_fingerprint(self, text: str) -> Optional[str]:
        # Generic explicit transitions. States are learned from the text,
        # rather than from a hardcoded workflow list.
        state = r"([a-z][a-z0-9_]*(?:\s+[a-z][a-z0-9_]*){0,1})"
        pattern = rf"\b{state}\s*(?:->|\bto\b|\binto\b)\s*{state}\b"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None

        source = self._clean_concept(match.group(1))
        target = self._clean_concept(match.group(2).split()[0])
        if not source or not target:
            return None
        return f"TRANSITION|{source}|TO|{target}"

    # ------------------------------------------------------------------
    # Semantic / fuzzy matching
    # ------------------------------------------------------------------

    def _match_by_business_rule_fingerprint(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        new_fp = self._business_rule_fingerprints(new_case)
        if not new_fp:
            return None

        candidates: List[Tuple[float, int]] = []
        structured_candidates: List[int] = []
        new_value_fingerprints = {
            value for value in new_fp if value.startswith("VALUE|")
        }
        new_value_rules = {
            tuple(parts[2:])
            for value in new_value_fingerprints
            if len(parts := value.split("|")) == 5
        }
        new_transitions = {
            (parts[1], parts[3])
            for value in new_fp
            if len(parts := value.split("|")) == 4
            and parts[0] == "TRANSITION"
            and parts[2] == "TO"
        }
        new_is_boundary = self._coverage_polarity(
            self._normalize_rule_text(self._case_text(new_case))
        ) == "EDGE"

        for index, existing_case in enumerate(existing_cases):
            if index in matched_existing:
                continue
            old_fp = self._business_rule_fingerprints(existing_case)
            if not old_fp or self._business_rules_conflict(new_case, existing_case):
                continue

            old_value_fingerprints = {
                value for value in old_fp if value.startswith("VALUE|")
            }
            old_value_rules = {
                tuple(parts[2:])
                for value in old_value_fingerprints
                if len(parts := value.split("|")) == 5
            }
            old_transitions = {
                (parts[1], parts[3])
                for value in old_fp
                if len(parts := value.split("|")) == 4
                and parts[0] == "TRANSITION"
                and parts[2] == "TO"
            }
            shared_value_constraint = bool(
                new_value_rules.intersection(old_value_rules)
            )
            shared_transition_destination = bool(
                {target for _, target in new_transitions}
                .intersection(target for _, target in old_transitions)
            )
            # A text-derived transition source can be noisy. Require the
            # surrounding case content to support the same identity even
            # when both cases share the same numeric rule and destination;
            # otherwise a broad rule case can consume a more specific case.
            coverage_score = self._coverage_similarity(
                self._business_coverage_identity(new_case) or (),
                self._business_coverage_identity(existing_case) or (),
            )
            both_boundary_cases = (
                new_is_boundary
                and self._coverage_polarity(
                    self._normalize_rule_text(self._case_text(existing_case))
                ) == "EDGE"
            )
            minimum_coverage = 0.35 if both_boundary_cases else 0.40
            if (
                shared_value_constraint
                and shared_transition_destination
                and coverage_score >= minimum_coverage
            ):
                structured_candidates.append(index)

            intersection = new_fp.intersection(old_fp)
            if not intersection:
                continue
            if not any(
                not fingerprint.startswith("TRANSITION|")
                for fingerprint in intersection
            ):
                # A shared destination label is not sufficient identity by
                # itself.
                continue

            score = len(intersection) / max(len(new_fp), len(old_fp))
            # A complete fingerprint set is high confidence. Partial matches
            # are allowed only when they represent most of both cases.
            if score >= 0.75:
                candidates.append((score, index))

        if not candidates:
            if not structured_candidates:
                return None
            return self._best_candidate_by_secondary_identity(
                new_case, structured_candidates, existing_cases
            )

        # Add the strong structured identity candidates without letting noisy
        # extra fingerprints dilute their exact shared rule evidence.
        candidate_indexes = {index for _, index in candidates}
        for index in structured_candidates:
            if index not in candidate_indexes:
                candidates.append((0.80, index))

        candidates.sort(key=lambda item: item[0], reverse=True)
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.05:
            tied_indexes = [
                index for score, index in candidates
                if candidates[0][0] - score < 0.05
            ]
            return self._best_candidate_by_secondary_identity(
                new_case, tied_indexes, existing_cases
            )
        return candidates[0][1]

    def _match_by_semantic_identity(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        candidates: List[Tuple[float, int]] = []
        for index, existing_case in enumerate(existing_cases):
            if index in matched_existing:
                continue
            if self._business_rules_conflict(new_case, existing_case):
                continue
            score = self._semantic_similarity(new_case, existing_case)
            if score >= self.SEMANTIC_MATCH_THRESHOLD:
                candidates.append((score, index))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.05:
            return None
        return candidates[0][1]

    def _match_by_fuzzy_identity(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        candidates = self._rank_fuzzy_candidates(
            new_case,
            existing_cases,
            matched_existing,
            minimum_score=self.FUZZY_MATCH_THRESHOLD,
            minimum_scenario_score=self.FUZZY_SCENARIO_THRESHOLD,
        )
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < self.FUZZY_MARGIN:
            return None
        return candidates[0][1]

    def _find_ambiguous_fuzzy_candidate(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        candidates = self._rank_fuzzy_candidates(
            new_case,
            existing_cases,
            matched_existing,
            minimum_score=0.65,
            minimum_scenario_score=0.65,
        )
        candidates.sort(key=lambda item: item[0], reverse=True)
        if (
            len(candidates) > 1
            and candidates[0][0] - candidates[1][0] < self.FUZZY_MARGIN
        ):
            return candidates[0][1]
        return None

    def _find_conflicting_fuzzy_candidate(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
    ) -> Optional[int]:
        candidates = self._rank_fuzzy_candidates(
            new_case,
            existing_cases,
            matched_existing,
            minimum_score=0.65,
            minimum_scenario_score=0.65,
            conflicting_only=True,
        )
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _rank_fuzzy_candidates(
        self,
        new_case: Any,
        existing_cases: Sequence[Any],
        matched_existing: Set[int],
        *,
        minimum_score: float,
        minimum_scenario_score: float,
        conflicting_only: bool = False,
    ) -> List[Tuple[float, int]]:
        candidates: List[Tuple[float, int]] = []
        new_module = self._normalize_text(self._field(new_case, "module"))
        new_scenario = self._normalize_text(self._field(new_case, "scenario"))

        for index, existing_case in enumerate(existing_cases):
            if index in matched_existing:
                continue
            has_rule_conflict = self._business_rules_conflict(
                new_case, existing_case
            )
            if has_rule_conflict != conflicting_only:
                continue

            old_module = self._normalize_text(self._field(existing_case, "module"))
            old_scenario = self._normalize_text(self._field(existing_case, "scenario"))
            module_score = self._similarity(new_module, old_module)
            scenario_score = self._similarity(new_scenario, old_scenario)
            token_score = self._token_similarity(
                self._case_text(new_case), self._case_text(existing_case)
            )
            numeric_score = self._numeric_similarity(
                self._case_text(new_case), self._case_text(existing_case)
            )
            score = (
                module_score * 0.20
                + scenario_score * 0.50
                + token_score * 0.20
                + numeric_score * 0.10
            )

            if scenario_score < minimum_scenario_score:
                continue
            if score < minimum_score:
                continue
            candidates.append((score, index))
        return candidates

    def _semantic_similarity(self, new_case: Any, existing_case: Any) -> float:
        new_text = self._case_text(new_case)
        old_text = self._case_text(existing_case)
        semantic_score = self._jaccard(
            self._semantic_tokens(new_text), self._semantic_tokens(old_text)
        )
        state_score = self._jaccard(
            self._extract_states(new_text), self._extract_states(old_text)
        )
        api_score = self._jaccard(
            self._extract_api_signals(new_text), self._extract_api_signals(old_text)
        )
        sequence_score = self._similarity(
            self._normalize_text(new_text), self._normalize_text(old_text)
        )
        module_score = self._similarity(
            self._normalize_text(self._field(new_case, "module")),
            self._normalize_text(self._field(existing_case, "module")),
        )
        numeric_score = self._numeric_similarity(new_text, old_text)

        return min(
            0.35 * semantic_score
            + 0.10 * state_score
            + 0.15 * api_score
            + 0.20 * sequence_score
            + 0.10 * module_score
            + 0.10 * numeric_score,
            1.0,
        )

    def _anchor_bonus(self, new_tokens: Set[str], old_tokens: Set[str]) -> float:
        # Compatibility helper. Anchors are generic shared tokens, not a
        # business-domain allowlist.
        shared = new_tokens.intersection(old_tokens)
        return min(1.0, len(shared) / 10.0) if shared else 0.0

    # ------------------------------------------------------------------
    # Conflict protection
    # ------------------------------------------------------------------

    def _business_rules_conflict(self, new_case: Any, existing_case: Any) -> bool:
        new_fp = self._business_rule_fingerprints(new_case)
        old_fp = self._business_rule_fingerprints(existing_case)
        if not new_fp or not old_fp:
            return False

        # A boundary-specific case and a general threshold case can share
        # the same extracted number and transition. They still test distinct
        # conditions, so do not let the shared transition fingerprint turn
        # the boundary case into a MODIFY of the broader case.
        new_text = self._normalize_rule_text(self._case_text(new_case))
        old_text = self._normalize_rule_text(self._case_text(existing_case))
        new_is_boundary = self._coverage_polarity(new_text) == "EDGE"
        old_is_boundary = self._coverage_polarity(old_text) == "EDGE"
        if new_is_boundary != old_is_boundary:
            def value_shapes(fingerprints: Set[str]) -> Set[Tuple[str, ...]]:
                return {
                    tuple(parts[2:])
                    for value in fingerprints
                    if len(parts := value.split("|")) == 5
                    and parts[0] == "VALUE"
                }

            def transition_targets(fingerprints: Set[str]) -> Set[str]:
                return {
                    parts[3]
                    for value in fingerprints
                    if len(parts := value.split("|")) == 4
                    and parts[0] == "TRANSITION"
                    and parts[2] == "TO"
                }

            if (
                value_shapes(new_fp).intersection(value_shapes(old_fp))
                and transition_targets(new_fp).intersection(
                    transition_targets(old_fp)
                )
            ):
                return True

        new_by_family = self._group_fingerprints(new_fp)
        old_by_family = self._group_fingerprints(old_fp)

        for family in set(new_by_family).intersection(old_by_family):
            if family == "VALUE":
                if self._value_constraints_conflict(
                    new_by_family[family], old_by_family[family]
                ):
                    return True
                continue

            if family == "TRANSITION":
                if self._transition_constraints_conflict(
                    new_by_family[family], old_by_family[family]
                ):
                    return True
                continue

            if new_by_family[family].isdisjoint(old_by_family[family]):
                return True
        return False

    def _value_constraints_conflict(
        self,
        new_fingerprints: Set[str],
        existing_fingerprints: Set[str],
    ) -> bool:
        """Return True when the same subject has different value rules.

        Numeric fingerprints include a short text-derived concept. That
        concept can vary with sentence structure even when both cases
        describe the same constraint. Only treat two rules as contradictory
        when their concepts identify the same subject and their
        operator/value/unit parts differ.
        """
        parsed_new = [
            self._parse_value_fingerprint(value)
            for value in new_fingerprints
        ]
        parsed_existing = [
            self._parse_value_fingerprint(value)
            for value in existing_fingerprints
        ]

        related_rules = []
        for new_value in parsed_new:
            if new_value is None:
                continue
            new_concept, new_rule = new_value
            for existing_value in parsed_existing:
                if existing_value is None:
                    continue
                existing_concept, existing_rule = existing_value
                if not self._same_rule_concept(new_concept, existing_concept):
                    continue
                related_rules.append((new_rule, existing_rule))

        # A test can mention both its input value and the rule threshold.
        # If the cases share at least one identical rule for that subject,
        # additional extracted values alone do not make them contradictory.
        if not related_rules:
            return False
        return not any(
            new_rule == existing_rule
            for new_rule, existing_rule in related_rules
        )

    @staticmethod
    def _transition_constraints_conflict(
        new_fingerprints: Set[str],
        existing_fingerprints: Set[str],
    ) -> bool:
        """Only flag transitions that disagree on the destination for a source."""
        def parse(fingerprint: str) -> Optional[Tuple[str, str]]:
            parts = fingerprint.split("|")
            if len(parts) != 4 or parts[0] != "TRANSITION" or parts[2] != "TO":
                return None
            return parts[1], parts[3]

        new_transitions = [parse(value) for value in new_fingerprints]
        old_transitions = [parse(value) for value in existing_fingerprints]
        for new_transition in new_transitions:
            if new_transition is None:
                continue
            new_source, new_target = new_transition
            for old_transition in old_transitions:
                if old_transition is None:
                    continue
                old_source, old_target = old_transition
                if new_source == old_source and new_target != old_target:
                    return True
        return False

    @staticmethod
    def _parse_value_fingerprint(
        fingerprint: str,
    ) -> Optional[Tuple[str, Tuple[str, ...]]]:
        parts = fingerprint.split("|")
        if len(parts) != 5 or parts[0] != "VALUE":
            return None
        return parts[1], tuple(parts[2:])

    def _same_rule_concept(self, left: str, right: str) -> bool:
        """Compare extracted rule subjects while tolerating extra context words."""
        left_tokens = {
            token for token in re.split(r"[_\s]+", left.casefold())
            if token and token not in self.STOPWORDS
        }
        right_tokens = {
            token for token in re.split(r"[_\s]+", right.casefold())
            if token and token not in self.STOPWORDS
        }
        if not left_tokens or not right_tokens:
            return False
        if left_tokens == right_tokens:
            return True

        shared = left_tokens.intersection(right_tokens)
        # A shared single token is too broad (for example, two unrelated
        # fields both containing "number"). Require a strong multi-token
        # overlap when the extracted phrases are not identical.
        return len(shared) >= 2 and (
            len(shared) / min(len(left_tokens), len(right_tokens)) >= 0.5
        )

    @staticmethod
    def _group_fingerprints(fingerprints: Set[str]) -> Dict[str, Set[str]]:
        grouped: Dict[str, Set[str]] = {}
        for fingerprint in fingerprints:
            family = fingerprint.split("|", 1)[0]
            grouped.setdefault(family, set()).add(fingerprint)
        return grouped

    # ------------------------------------------------------------------
    # Case / text utilities
    # ------------------------------------------------------------------

    def _case_text(self, test_case: Any) -> str:
        # Identity and rule extraction use only business-content fields.
        # Classification metadata such as priority or automation type must
        # never become business identity.
        fields = ("module", "scenario", "test_steps", "expected_result")
        return " ".join(
            str(self._field(test_case, field_name))
            for field_name in fields
            if self._field(test_case, field_name) is not None
        )

    def _semantic_tokens(self, text: str) -> Set[str]:
        normalized = self._normalize_text(text)
        raw_tokens = set(re.findall(r"[a-z0-9_]+", normalized))
        tokens = {
            token for token in raw_tokens
            if token not in self.STOPWORDS and len(token) > 2
        }

        # Add generic two-word concepts to retain meaning such as
        # "order status" or "payment method" without hardcoded vocabulary.
        words = normalized.split()
        for left, right in zip(words, words[1:]):
            if (
                left not in self.STOPWORDS
                and right not in self.STOPWORDS
                and len(left) > 2
                and len(right) > 2
            ):
                tokens.add(f"{left}_{right}")
        return tokens

    def _extract_states(self, text: str) -> Set[str]:
        states: Set[str] = set()
        normalized = self._normalize_text(text)
        for match in re.finditer(
            r"\b([a-z][a-z0-9_]*(?:\s+[a-z][a-z0-9_]*){0,1})\s*(?:->|\bto\b|\binto\b)\s*"
            r"([a-z][a-z0-9_]*)\b",
            normalized,
            flags=re.IGNORECASE,
        ):
            states.add(self._clean_concept(match.group(1)))
            states.add(self._clean_concept(match.group(2)))
        return {state for state in states if state}

    def _extract_api_signals(self, text: str) -> Set[str]:
        normalized = self._normalize_text(text)
        signals: Set[str] = set()
        method = self._extract_api_method(normalized)
        if method:
            signals.add(f"method:{method}")
        status = self._extract_http_status(normalized)
        if status:
            signals.add(f"status:{status}")
        endpoint = re.search(r"/[a-z0-9_\-./{}]+", normalized, flags=re.IGNORECASE)
        if endpoint:
            signals.add(f"endpoint:{endpoint.group(0).rstrip('.,;:')}")
        if self._contains_any(normalized, {"retry", "retries", "retrying"}):
            signals.add("retry")
        return signals

    def _normalized_requirement_reference(self, test_case: Any) -> str:
        value = self._field(test_case, "requirement_reference")
        return self._normalize_text(value) if value is not None else ""

    def _exact_identity(self, new_case: Any, existing_case: Any) -> bool:
        return (
            bool(self._normalize_text(self._field(new_case, "module")))
            and bool(self._normalize_text(self._field(new_case, "scenario")))
            and self._normalize_text(self._field(new_case, "module"))
            == self._normalize_text(self._field(existing_case, "module"))
            and self._normalize_text(self._field(new_case, "scenario"))
            == self._normalize_text(self._field(existing_case, "scenario"))
        )

    def _content_equal(self, new_case: Any, existing_case: Any) -> bool:
        for field_name in self._FIELDS_FOR_CONTENT:
            if self._normalize_content(self._field(new_case, field_name)) != self._normalize_content(
                self._field(existing_case, field_name)
            ):
                return False
        return True

    def _normalize_content(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).replace("\\<br>", "<br>")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\s+", " ", text)
        return text.strip().casefold()

    def _normalize_rule_text(self, text: str) -> str:
        text = self._normalize_text(text)
        replacements = {" ": " ", "–": "-", "—": "-", "≤": "<=", "≥": ">=", "→": "->", "％": "%"}
        for source, target in replacements.items():
            text = text.replace(source, target)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).casefold()
        text = text.replace("\\<br>", " ").replace("<br>", " ")
        text = text.replace("‑", "-").replace("–", "-").replace("—", "-")
        text = text.replace("→", " -> ")
        text = re.sub(r"[^a-z0-9_./%><=+\- ]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_number(self, value: str) -> Optional[str]:
        try:
            number = float(value)
            if number.is_integer():
                return str(int(number))
            return f"{number:.10f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return None

    def _display_id(self, test_case: Any) -> str:
        value = self._field(test_case, "test_case_id")
        return str(value) if value else "NEW"

    @staticmethod
    def _field(obj: Any, name: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # ------------------------------------------------------------------
    # Similarity helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio()

    def _token_similarity(self, left: str, right: str) -> float:
        left_tokens = {t for t in self._normalize_text(left).split() if t not in self.STOPWORDS}
        right_tokens = {t for t in self._normalize_text(right).split() if t not in self.STOPWORDS}
        return self._jaccard(left_tokens, right_tokens)

    def _numeric_similarity(self, left: str, right: str) -> float:
        left_numbers = set(re.findall(r"\d+(?:\.\d+)?", self._normalize_text(left)))
        right_numbers = set(re.findall(r"\d+(?:\.\d+)?", self._normalize_text(right)))
        if not left_numbers and not right_numbers:
            return 1.0
        if not left_numbers or not right_numbers:
            return 0.0
        return self._jaccard(left_numbers, right_numbers)

    @staticmethod
    def _jaccard(left: Set[str], right: Set[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return len(left.intersection(right)) / len(left.union(right))

    def _best_candidate_by_secondary_identity(
        self,
        new_case: Any,
        candidates: Sequence[int],
        existing_cases: Sequence[Any],
    ) -> Optional[int]:
        scored: List[Tuple[float, int]] = []
        for index in candidates:
            existing_case = existing_cases[index]
            score = (
                0.45 * self._similarity(
                    self._normalize_text(self._field(new_case, "test_steps")),
                    self._normalize_text(self._field(existing_case, "test_steps")),
                )
                + 0.35 * self._similarity(
                    self._normalize_text(self._field(new_case, "expected_result")),
                    self._normalize_text(self._field(existing_case, "expected_result")),
                )
                + 0.20 * self._similarity(
                    self._normalize_text(self._field(new_case, "module")),
                    self._normalize_text(self._field(existing_case, "module")),
                )
            )
            scored.append((score, index))
        if not scored:
            return None
        scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        return scored[0][1]

    # ------------------------------------------------------------------
    # Generic extraction helpers
    # ------------------------------------------------------------------

    def _extract_api_method(self, text: str) -> Optional[str]:
        for method in self.API_METHODS:
            if re.search(rf"\b{method}\b", text, flags=re.IGNORECASE):
                return method
        return None

    def _extract_http_status(self, text: str) -> Optional[str]:
        match = re.search(self.HTTP_STATUS_PATTERN, text, flags=re.IGNORECASE)
        if not match:
            return None
        status = match.group(1)
        # Only treat plausible HTTP status codes as HTTP signals when the
        # surrounding text indicates HTTP/API semantics.
        if not re.search(r"\b(?:http|status|response|api|endpoint)\b", text):
            return None
        return status

    def _extract_retry_count(self, text: str) -> Optional[int]:
        patterns = [
            r"retry(?:s|ing)?\s+(?:up to|for)\s+(\d+)",
            r"(\d+)\s+(?:retries|retry attempts)",
            r"exactly\s+(\d+)\s+retries",
            r"retry\s+the\s+request\s+(\d+)\s+times",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None

    def _operator_from_match(self, text: str) -> Optional[str]:
        lowered = text.casefold()
        if re.search(r"(greater than|more than|above|over|>=|>)", lowered):
            return "GT"
        if re.search(r"(less than|below|under|<=|<)", lowered):
            return "LT"
        if re.search(r"(equal to|equals|exactly|=)", lowered):
            return "EXACT"
        return None

    def _canonical_operator(self, operator: str) -> str:
        operator = operator.casefold().strip()
        if operator in {">", ">=", "gt", "greater than", "more than", "above", "over"}:
            return "GT"
        if operator in {"<", "<=", "lt", "less than", "below", "under"}:
            return "LT"
        if operator in {"=", "exact", "exactly", "equal to", "equals"}:
            return "EXACT"
        return operator.upper()

    def _clean_concept(self, value: str) -> str:
        tokens = [
            token for token in self._normalize_text(value).split()
            if token not in self.STOPWORDS
        ]
        return "_".join(tokens[:5])

    def _canonical_state(self, value: str) -> str:
        return self._clean_concept(value).upper()

    def _contains_any(self, text: str, phrases: Iterable[str]) -> bool:
        return any(self._contains_phrase(text, phrase) for phrase in phrases)

    def _contains_phrase(self, text: str, phrase: str) -> bool:
        normalized_phrase = self._normalize_text(phrase)
        if not normalized_phrase:
            return False
        if " " in normalized_phrase:
            return normalized_phrase in text
        return bool(re.search(rf"\b{re.escape(normalized_phrase)}\b", text, flags=re.IGNORECASE))
