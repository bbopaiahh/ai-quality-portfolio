from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from models.requirement import Requirement
    from models.test_case import TestCase
    from models.traceability import Traceability


@dataclass
class DuplicateCandidate:
    first_test_case_id: str
    second_test_case_id: str
    similarity: float
    reason: str


class TestSuiteQualityAnalyzer:
    """
    Deterministic quality analysis for the active Master Test Suite.

    Important design rule:
        Missing test-type diversity is a quality signal, not automatically
        a coverage gap. A requirement does not need Positive + Negative +
        Edge + E2E tests simply because those four test types exist.

    The analyzer therefore distinguishes:
        - CRITICAL: a meaningful coverage/risk gap exists.
        - CONCERN: coverage exists, but the requirement could be strengthened.

    The public result structure remains compatible with the previous
    implementation so the Streamlit application does not need to change.
    """

    SUPPORTED_AUTOMATION_TYPES = {
        "UI Automation",
        "API Automation",
        "Backend/DB",
    }

    EXPECTED_TEST_TYPES = {
        "Positive Case",
        "Negative Case",
        "Edge Case",
        "E2E Case",
    }

    RISK_KEYWORDS = {
        "negative": (
            "reject", "rejected", "prevent", "prevents", "block",
            "blocks", "invalid", "unauthorized", "cannot", "must not",
            "not allowed", "fails", "failure", "below", "above",
            "less than", "greater than", "mandatory", "required",
        ),
        "boundary": (
            "threshold", "boundary", "exactly", "equal to", "greater than",
            "less than", "at least", "at most", "no more than", "no less than",
            "more than", "fewer than", "under ", "over ", "within ",
            "outside ", "exceeds", "exceeding", "maximum", "minimum",
            "max ", "min ", "limit", "range", "between ", "up to ",
        ),
        "workflow": (
            "workflow", "state machine", "state transition", "transition",
            "pipeline", "end-to-end", "e2e", "journey", "flow",
        ),
        "security": (
            "security", "encrypt", "encrypted", "encryption", "pii", "authentication",
            "authorization", "token", "access control", "unauthorized",
        ),
        "performance": (
            "performance", "response time", "load time", "load under", "load in",
            "latency", "throughput", "p95", "p99", "requests per second",
            "requests/sec", "transactions per second", "tps", "rps",
            "concurrent users", "respond within", "return within",
            "complete within", "process within", "resolve within", "resolve in",
            "uptime", "availability target",
        ),
        "api": (
            "api", "endpoint", "http", "request", "response", "payload",
        ),
    }

    def __init__(self, duplicate_threshold: float = 0.90):
        if not 0 < duplicate_threshold <= 1:
            raise ValueError(
                "duplicate_threshold must be greater than 0 and at most 1."
            )
        self.duplicate_threshold = duplicate_threshold

    def analyze(
        self,
        requirements: List[Requirement],
        test_cases: List[TestCase],
        mappings: List[Traceability],
    ) -> Dict[str, object]:
        active_requirements = [
            requirement
            for requirement in requirements
            if requirement.status == "ACTIVE"
        ]
        active_test_cases = [
            test_case
            for test_case in test_cases
            if test_case.status == "ACTIVE"
        ]
        active_mappings = [
            mapping
            for mapping in mappings
            if mapping.status == "ACTIVE"
        ]

        test_case_by_id = {
            test_case.test_case_id: test_case
            for test_case in active_test_cases
        }

        requirement_mapping_map = self._build_requirement_mapping_map(
            active_requirements,
            active_mappings,
            test_case_by_id,
        )

        duplicate_candidates = self._find_duplicate_candidates(active_test_cases)
        requirement_gaps = self._find_requirement_gaps(
            active_requirements,
            requirement_mapping_map,
        )
        priority_analysis = self._analyze_priority_coverage(
            active_requirements,
            requirement_mapping_map,
        )
        automation_analysis = self._analyze_automation_coverage(active_test_cases)
        test_type_analysis = self._analyze_test_type_coverage(active_test_cases)

        quality_score = self._calculate_quality_score(
            active_requirements=active_requirements,
            active_test_cases=active_test_cases,
            duplicate_candidates=duplicate_candidates,
            requirement_gaps=requirement_gaps,
            priority_analysis=priority_analysis,
            automation_analysis=automation_analysis,
        )

        critical_gaps = [
            gap for gap in requirement_gaps
            if gap["severity"] == "CRITICAL"
        ]
        concerns = [
            gap for gap in requirement_gaps
            if gap["severity"] == "CONCERN"
        ]

        return {
            "summary": {
                "total_requirements": len(active_requirements),
                "total_test_cases": len(active_test_cases),
                "duplicate_candidates": len(duplicate_candidates),
                # Kept for backward compatibility. This now means
                # requirements requiring review, not necessarily uncovered.
                "requirements_with_gaps": len(requirement_gaps),
                "requirements_requiring_review": len(requirement_gaps),
                "critical_coverage_gaps": len(critical_gaps),
                "quality_concerns": len(concerns),
                "single_test_requirements": sum(
                    1 for gap in requirement_gaps if gap["single_test_case"]
                ),
                "quality_score": quality_score,
            },
            "duplicates": duplicate_candidates,
            "requirement_gaps": requirement_gaps,
            "critical_coverage_gaps": critical_gaps,
            "quality_concerns": concerns,
            "priority_analysis": priority_analysis,
            "automation_analysis": automation_analysis,
            "test_type_analysis": test_type_analysis,
        }

    def _build_requirement_mapping_map(
        self,
        requirements: List[Requirement],
        mappings: List[Traceability],
        test_case_by_id: Dict[str, TestCase],
    ) -> Dict[str, List[TestCase]]:
        result = {requirement.requirement_id: [] for requirement in requirements}

        for mapping in mappings:
            if mapping.requirement_id not in result:
                continue
            test_case = test_case_by_id.get(mapping.test_case_id)
            if test_case is None:
                continue
            if test_case not in result[mapping.requirement_id]:
                result[mapping.requirement_id].append(test_case)

        return result

    def _find_duplicate_candidates(
        self,
        test_cases: List[TestCase],
    ) -> List[DuplicateCandidate]:
        candidates = []
        for index, first in enumerate(test_cases):
            first_text = self._identity_text(first)
            for second in test_cases[index + 1:]:
                second_text = self._identity_text(second)
                similarity = SequenceMatcher(None, first_text, second_text).ratio()
                if similarity >= self.duplicate_threshold:
                    candidates.append(
                        DuplicateCandidate(
                            first_test_case_id=first.test_case_id,
                            second_test_case_id=second.test_case_id,
                            similarity=round(similarity, 4),
                            reason="Scenario content is highly similar.",
                        )
                    )
        return candidates

    def _find_requirement_gaps(
        self,
        requirements: List[Requirement],
        requirement_mapping_map: Dict[str, List[TestCase]],
    ) -> List[Dict[str, object]]:
        findings = []

        for requirement in requirements:
            mapped_cases = requirement_mapping_map.get(requirement.requirement_id, [])
            assessment = self._assess_requirement(requirement, mapped_cases)
            if assessment["reasons"]:
                findings.append(
                    {
                        "requirement_id": requirement.requirement_id,
                        "module": requirement.module,
                        "requirement": requirement.requirement,
                        "priority": requirement.priority,
                        "mapped_test_cases": [
                            test_case.test_case_id for test_case in mapped_cases
                        ],
                        "mapped_test_case_count": len(mapped_cases),
                        "test_types_present": sorted(
                            {test_case.test_type for test_case in mapped_cases}
                        ),
                        "missing_test_types": assessment["missing_test_types"],
                        "single_test_case": len(mapped_cases) == 1,
                        "severity": assessment["severity"],
                        "gap_reasons": assessment["reasons"],
                    }
                )

        return findings

    def _assess_requirement(
        self,
        requirement: Requirement,
        mapped_cases: List[TestCase],
    ) -> Dict[str, object]:
        text = str(requirement.requirement or "").casefold()
        test_types = {test_case.test_type for test_case in mapped_cases}
        reasons: List[str] = []
        severity = "CONCERN"

        if not mapped_cases:
            return {
                "severity": "CRITICAL",
                "reasons": ["No mapped test cases"],
                "missing_test_types": sorted(self.EXPECTED_TEST_TYPES),
            }

        risk_flags = {
            name: self._contains_any(text, keywords)
            for name, keywords in self.RISK_KEYWORDS.items()
        }
        # Boundary risk must be derived from the requirement itself.
        # Do not depend on example values from a particular domain.
        risk_flags["boundary"] = risk_flags["boundary"] or self._contains_measurable_boundary(text)

        # A single test is a review signal, not automatically a coverage gap.
        if len(mapped_cases) == 1 and requirement.priority in {"P0", "P1"}:
            reasons.append("Only one mapped test case for a high-priority requirement")

        # Restrictive rules and validation requirements benefit from negative tests.
        if risk_flags["negative"] and "Negative Case" not in test_types:
            reasons.append("No negative test coverage for a restrictive/validation rule")

        # Boundary coverage is only expected when the requirement actually
        # contains a measurable limit, threshold, or boundary condition.
        if risk_flags["boundary"] and "Edge Case" not in test_types:
            reasons.append("No edge test coverage for a stated boundary/threshold")

        # Workflow/E2E is only recommended when the requirement explicitly
        # describes an end-to-end flow. Generic workflow/state requirements do
        # not automatically require a full E2E test.
        explicit_e2e = any(
            phrase in text
            for phrase in ("end-to-end", "e2e", "complete flow", "full flow")
        )
        if explicit_e2e and "E2E Case" not in test_types:
            reasons.append("No E2E test coverage for an explicitly end-to-end requirement")

        # Risk-specific implementation checks. These are concerns rather than
        # blanket test-type requirements.
        if risk_flags["performance"] and not any(
            test_case.automation_type == "Backend/DB"
            for test_case in mapped_cases
        ):
            reasons.append("Performance requirement has no Backend/DB test")

        if risk_flags["security"] and not any(
            test_case.automation_type in {"Backend/DB", "API Automation"}
            for test_case in mapped_cases
        ):
            reasons.append("Security requirement has no backend/API validation")

        if risk_flags["api"] and not any(
            test_case.automation_type == "API Automation"
            for test_case in mapped_cases
        ):
            reasons.append("API requirement has no API automation coverage")

        # Keep a small, useful concern for high-priority requirements with
        # multiple tests but no negative/risk-specific coverage.
        if requirement.priority == "P0" and not reasons:
            if len(mapped_cases) < 2:
                reasons.append("P0 requirement has limited test depth")

        missing_types = sorted(self.EXPECTED_TEST_TYPES - test_types)
        return {
            "severity": severity,
            "reasons": reasons,
            "missing_test_types": missing_types,
        }

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword.casefold() in text for keyword in keywords)

    @staticmethod
    def _contains_measurable_boundary(text: str) -> bool:
        """Return True when a requirement expresses a measurable constraint.

        This deliberately detects the *shape* of a measurable rule rather
        than hard-coding domain examples such as a particular digit count,
        duration, retry count, record count, distance, or currency value.
        """
        numeric = r"\d+(?:\.\d+)?"
        magnitude = r"(?:[kKmMbBgGtT](?:illion|[bB])?)?"
        unit = (
            r"(?:%|percent|seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|"
            r"months?|years?|milliseconds?|ms|meters?|metres?|km|kilometers?|"
            r"kilometres?|miles?|items?|records?|users?|requests?|transactions?|"
            r"attempts?|retries?|digits?|characters?|bytes?|kb|mb|gb|tps|rps)"
        )
        measurable = rf"{numeric}{magnitude}"
        measurable_with_unit = rf"{numeric}{magnitude}\s*-?\s*(?:{unit})"

        patterns = (
            rf"\b(?:at least|at most|no more than|no less than|less than|greater than|"
            rf"more than|fewer than|under|over|within|outside|up to|exceeds?|"
            rf"equal to|exactly)\s+{measurable_with_unit}(?!\w)",
            rf"\b(?:minimum|maximum|max|min|limit|threshold)\b(?:\s+\w+){{0,5}}\s*[:=]?\s*"
            rf"(?:{measurable_with_unit}|{measurable})(?!\w)",
            rf"\b{measurable}\s*(?:-|to|through)\s*{measurable_with_unit}(?!\w)",
            rf"\b{measurable_with_unit}(?!\w)",
            rf"\b(?:between|from)\s+{measurable_with_unit}\s+(?:and|to)\s+"
            rf"{measurable_with_unit}(?!\w)",
        )

        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _analyze_priority_coverage(
        self,
        requirements: List[Requirement],
        requirement_mapping_map: Dict[str, List[TestCase]],
    ) -> Dict[str, object]:
        result = {
            "P0": {"total": 0, "covered_by_p0_p1": 0, "gaps": []},
            "P1": {"total": 0, "covered_by_p0_p1": 0, "gaps": []},
            "P2": {"total": 0, "covered_by_p0_p1": 0, "gaps": []},
        }

        for requirement in requirements:
            priority = requirement.priority
            if priority not in result:
                continue
            result[priority]["total"] += 1
            mapped_cases = requirement_mapping_map.get(requirement.requirement_id, [])
            has_high_priority_test = any(
                test_case.priority in {"P0", "P1"}
                for test_case in mapped_cases
            )
            if has_high_priority_test:
                result[priority]["covered_by_p0_p1"] += 1
            else:
                result[priority]["gaps"].append(requirement.requirement_id)

        return result

    def _analyze_automation_coverage(
        self,
        test_cases: List[TestCase],
    ) -> Dict[str, object]:
        by_type = {
            automation_type: 0
            for automation_type in sorted(self.SUPPORTED_AUTOMATION_TYPES)
        }
        automated = 0
        manual_or_unknown = []

        for test_case in test_cases:
            automation_type = test_case.automation_type
            if automation_type in by_type:
                by_type[automation_type] += 1
                automated += 1
            else:
                manual_or_unknown.append(test_case.test_case_id)

        total = len(test_cases)
        percentage = (automated / total) * 100 if total else 0.0
        return {
            "total_test_cases": total,
            "automated_test_cases": automated,
            "manual_or_unknown_test_cases": len(manual_or_unknown),
            "automation_percentage": round(percentage, 2),
            "by_type": by_type,
            "manual_or_unknown_ids": manual_or_unknown,
        }

    def _analyze_test_type_coverage(
        self,
        test_cases: List[TestCase],
    ) -> Dict[str, object]:
        counts = {
            test_type: 0
            for test_type in sorted(self.EXPECTED_TEST_TYPES)
        }
        for test_case in test_cases:
            if test_case.test_type in counts:
                counts[test_case.test_type] += 1

        total = len(test_cases)
        percentages = {
            test_type: round((count / total) * 100, 2) if total else 0.0
            for test_type, count in counts.items()
        }
        return {
            "counts": counts,
            "percentages": percentages,
            "total_test_cases": total,
        }

    def _calculate_quality_score(
        self,
        *,
        active_requirements: List[Requirement],
        active_test_cases: List[TestCase],
        duplicate_candidates: List[DuplicateCandidate],
        requirement_gaps: List[Dict[str, object]],
        priority_analysis: Dict[str, object],
        automation_analysis: Dict[str, object],
    ) -> float:
        """
        Calculate a transparent 0-100 quality indicator.

        Weighting:
            Requirement coverage       : 40
            Risk-specific adequacy     : 25
            Priority coverage           : 15
            Automation coverage         : 10
            Duplicate health            : 10

        Missing test-type diversity is only penalized when the requirement
        actually calls for that risk treatment. Therefore 100% requirement
        coverage can still produce a high score without pretending that every
        requirement needs every test type.
        """
        total_requirements = len(active_requirements)
        if total_requirements == 0:
            requirement_coverage_score = 100.0
            risk_adequacy_score = 100.0
            priority_score = 100.0
        else:
            critical_count = sum(
                1 for gap in requirement_gaps
                if gap["severity"] == "CRITICAL"
            )
            requirement_coverage_score = max(
                0.0,
                100.0 - (critical_count / total_requirements) * 100.0,
            )

            concern_count = sum(
                1 for gap in requirement_gaps
                if gap["severity"] == "CONCERN"
            )
            risk_adequacy_score = max(
                0.0,
                100.0 - (concern_count / total_requirements) * 50.0,
            )

            priority_total = sum(
                data["total"] for data in priority_analysis.values()
            )
            priority_covered = sum(
                data["covered_by_p0_p1"] for data in priority_analysis.values()
            )
            priority_score = (
                (priority_covered / priority_total) * 100
                if priority_total
                else 100.0
            )

        automation_score = automation_analysis["automation_percentage"]

        total_test_cases = len(active_test_cases)
        duplicate_pairs = len(duplicate_candidates)
        if total_test_cases == 0:
            duplicate_score = 100.0
        else:
            duplicate_rate = min(duplicate_pairs / total_test_cases, 1.0)
            duplicate_score = (1.0 - duplicate_rate) * 100

        score = (
            requirement_coverage_score * 0.40
            + risk_adequacy_score * 0.25
            + priority_score * 0.15
            + automation_score * 0.10
            + duplicate_score * 0.10
        )
        return round(score, 2)

    @staticmethod
    def _identity_text(test_case: TestCase) -> str:
        return " ".join(
            [
                str(test_case.module or ""),
                str(test_case.scenario or ""),
            ]
        ).casefold().strip()
