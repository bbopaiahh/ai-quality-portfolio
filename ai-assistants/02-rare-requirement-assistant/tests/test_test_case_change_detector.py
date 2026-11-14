import unittest

from models.test_case import TestCase as DomainTestCase
from repository.test_case_change_detector import (
    ADD,
    MODIFY,
    RETIRE,
    REVIEW,
    TestCaseChangeDetector,
)
from repository.test_case_repository import (
    TestCaseRepository as RARETestCaseRepository,
)
from repository.test_case_version_manager import (
    TestCaseVersionManager as RARETestCaseVersionManager,
)


class TestCaseChangeDetectorRuleConflictTests(unittest.TestCase):
    def setUp(self):
        self.detector = TestCaseChangeDetector()

    @staticmethod
    def _case(
        test_case_id,
        module,
        scenario,
        test_steps,
        expected_result,
    ):
        return DomainTestCase(
            test_case_id=test_case_id,
            module=module,
            scenario=scenario,
            test_steps=test_steps,
            expected_result=expected_result,
            priority="P1",
            test_type="Negative Case",
            suite_type="Regression",
            automation_type="UI Automation",
        )

    def test_equivalent_numeric_rule_with_different_context_words_matches(self):
        generated = self._case(
            "GEN001",
            "Lead Capture",
            "Mobile number less than 10 digits",
            "Enter a mobile number with fewer than 10 digits",
            "Validation error is shown and lead remains in Draft",
        )
        existing = self._case(
            "TC003",
            "Lead Creation",
            "Validate mobile number with less than 10 digits",
            "Enter mobile number with less than 10 digits",
            "System displays validation error and keeps lead in Draft",
        )

        change = self.detector.detect_changes(
            [generated], [existing]
        )[0]

        self.assertEqual(MODIFY, change.action)
        self.assertEqual("TC003", change.test_case_id)

    def test_different_numeric_rule_for_same_subject_still_conflicts(self):
        generated = self._case(
            "GEN001",
            "Lead Capture",
            "Mobile number more than 10 digits",
            "Enter a mobile number with more than 10 digits",
            "Validation error is shown",
        )
        existing = self._case(
            "TC003",
            "Lead Creation",
            "Validate mobile number with less than 10 digits",
            "Enter mobile number with less than 10 digits",
            "System displays validation error",
        )

        self.assertTrue(
            self.detector._business_rules_conflict(generated, existing)
        )

    def test_strong_scenario_match_survives_module_and_wording_changes(self):
        generated = self._case(
            "TC006",
            "State Machine",
            "Verify that saving a Draft lead with a Mobile Number shorter than 10 digits is rejected and the lead remains in Draft.",
            "Enter a Mobile Number with fewer than 10 digits; select a product type and save.",
            "Validation error indicating Mobile Number must be 10 digits; lead stays in Draft state.",
        )
        existing = self._case(
            "TC002",
            "Lead Management",
            "Verify that saving a lead with a mobile number shorter than 10 digits triggers a validation error and the lead remains in Draft state.",
            "Enter a mobile number with 9 digits; select a product type and save.",
            "System displays a validation error for mobile number length; lead stays in Draft state.",
        )

        change = self.detector.detect_changes(
            [generated],
            [existing],
            generation_complete=True,
            retirement_candidates={"TC002"},
        )[0]

        self.assertEqual(MODIFY, change.action)
        self.assertEqual("TC002", change.test_case_id)

    def test_related_transition_and_numeric_case_requires_review_not_retirement(self):
        generated = self._case(
            "TC007",
            "State Machine",
            "Verify that Dedup_Check auto-check triggers transition to BM_Review when the PAN matches an existing record within the last 90 days.",
            "Run the automatic duplicate check; detect matching PAN within 90 days; transition the lead to BM_Review.",
            "Lead state changes to BM_Review.",
        )
        existing = self._case(
            "TC004",
            "Deduplication",
            "Verify that when a PAN or mobile number matches an existing record created within the last 90 days, the lead transitions from Dedup_Check to BM_Review state.",
            "Run the automatic duplicate check and observe the resulting state transition.",
            "Lead transitions to BM_Review state.",
        )

        changes = self.detector.detect_changes(
            [generated],
            [existing],
            generation_complete=True,
            retirement_candidates={"TC004"},
        )

        self.assertEqual(REVIEW, changes[0].action)
        self.assertEqual("TC004", changes[0].existing_test_case.test_case_id)
        self.assertIn("shares a measurable condition", changes[0].reason)
        self.assertNotIn(RETIRE, [change.action for change in changes])

    def test_shared_threshold_and_transition_match_despite_extra_extracted_values(self):
        generated = self._case(
            "GEN001",
            "Lead-to-Disbursement",
            "CIBIL score greater than 650 allows transition from Eligibility to Docs_Pending state",
            "Mock CIBIL API to return score 720; submit request",
            "System validates the score greater than 650 and moves lead to Docs_Pending",
        )
        existing = self._case(
            "TC047",
            "Lead-to-Disbursement (L2D) Pipeline",
            "CIBIL score greater than 650 allows transition from Eligibility to Docs_Pending state",
            "Mock the CIBIL API response with score 720 and submit request",
            "System receives score greater than 650 and moves the lead to Docs_Pending",
        )

        self.assertFalse(
            self.detector._business_rules_conflict(generated, existing)
        )
        change = self.detector.detect_changes(
            [generated], [existing]
        )[0]
        self.assertEqual(MODIFY, change.action)
        self.assertEqual("TC047", change.test_case_id)

    def test_matching_threshold_and_transition_match_despite_transition_source_noise(self):
        generated = self._case(
            "GEN001",
            "Lead-to-Disbursement",
            "Verify that when the entered PAN matches an existing record within the last 90 days, the system automatically moves the lead from Dedup_Check to BM_Review state.",
            "1. Save the lead to trigger Dedup_Check<br>2. Observe the system processing<br>3. Verify the resulting state displayed for the lead",
            "Lead transitions to BM_Review state; audit log records the state change.",
        )
        existing = self._case(
            "TC084",
            "Lead-to-Disbursement",
            "Deduplication triggers BM_Review when PAN matches an existing record within the last 90 days",
            "System performs automatic deduplication check; observe triggered action",
            "Lead transitions to BM_Review",
        )

        change = self.detector.detect_changes(
            [generated], [existing]
        )[0]
        self.assertEqual(MODIFY, change.action)
        self.assertEqual("TC084", change.test_case_id)

    def test_shared_generic_transition_does_not_match_unrelated_test(self):
        generated = self._case(
            "GEN001",
            "Lead-to-Disbursement",
            "OCR name mismatch blocks transition to Docs_Pending",
            "Return an OCR name that differs from the PAN name",
            "Lead remains in Eligibility because of name mismatch",
        )
        existing = self._case(
            "TC027",
            "Eligibility",
            "CIBIL score at or below 650 does not transition to Docs_Pending",
            "Mock the bureau API to return a CIBIL score of 600",
            "Lead remains in Eligibility because the score is too low",
        )

        change = self.detector.detect_changes(
            [generated], [existing]
        )[0]

        self.assertEqual(ADD, change.action)

    def test_unrelated_negative_test_does_not_match_through_empty_signals(self):
        generated = self._case(
            "GEN001",
            "Lead-to-Disbursement (L2D) - State Machine",
            "Verify that a lead in Draft state remains in Draft when an invalid mobile number is entered",
            "Open Lead creation screen; enter an invalid mobile number; select a product type; save the lead",
            "Validation error is shown and lead stays in Draft state",
        )
        existing = self._case(
            "TC099",
            "Lead-to-Disbursement (L2D)",
            "Verify that a mismatch between Karza OCR name and PAN name prevents transition from Eligibility",
            "Initiate bureau action; receive a CIBIL score and a Karza OCR name that does not match PAN",
            "Eligibility is rejected and the lead remains in Eligibility with a name mismatch message",
        )

        changes = self.detector.detect_changes([generated], [existing])

        self.assertEqual([ADD, REVIEW], [change.action for change in changes])
        self.assertEqual("TC099", changes[1].test_case_id)

    def test_boundary_case_does_not_replace_broader_threshold_case(self):
        generated = self._case(
            "GEN176",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify Dedup_Check boundary condition when matching record is exactly 90 days old",
            "Trigger System Auto-Check and evaluate the record match at the 90-day boundary",
            "A record exactly 90 days old is detected and transitions to BM_Review",
        )
        existing = self._case(
            "TC150",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify transition from Dedup_Check to BM_Review when a duplicate PAN or mobile is found within 90 days",
            "System performs auto-deduplication check, detects a matching record, and triggers transition",
            "Lead moves to BM_Review state",
        )

        changes = self.detector.detect_changes([generated], [existing])

        self.assertNotEqual(MODIFY, changes[0].action)
        self.assertEqual("TC150", changes[-1].test_case_id)
        self.assertEqual(REVIEW, changes[-1].action)

    def test_boundary_case_matches_existing_boundary_case_not_broad_case(self):
        generated = self._case(
            "GEN179",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify deduplication behavior on exact 90th day boundary match for PAN or Mobile number",
            "Initiate System Auto-Check and evaluate records created exactly 90 days ago",
            "Lead transitions to BM_Review state as the match falls within the 90 days threshold",
        )
        broad = self._case(
            "TC150",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify transition from Dedup_Check to BM_Review when a duplicate PAN or mobile is found within 90 days",
            "System performs auto-deduplication check, detects a matching record, and triggers transition",
            "Lead moves to BM_Review state",
        )
        boundary = self._case(
            "TC172",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify Dedup_Check boundary condition when matching record is exactly 90 days old",
            "Trigger System Auto-Check and evaluate the record match at the 90-day boundary",
            "A record exactly 90 days old is detected and transitions to BM_Review",
        )

        changes = self.detector.detect_changes([generated], [broad, boundary])

        self.assertEqual(MODIFY, changes[0].action)
        self.assertEqual("TC172", changes[0].test_case_id)
        self.assertEqual(REVIEW, changes[1].action)
        self.assertEqual("TC150", changes[1].test_case_id)

    def test_mobile_specific_case_matches_specific_case_not_broad_case(self):
        generated = self._case(
            "GEN178",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify lead transitions from Dedup_Check to BM_Review when Mobile matches an existing record created within the last 90 days",
            "Initiate System Auto-Check and evaluate Mobile number against existing records",
            "A Mobile number match within 90 days transitions the lead to BM_Review",
        )
        specific = self._case(
            "TC095",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify state transition when Mobile Number matches an existing record within the last 90 days",
            "Compare applicant Mobile Number against existing records within the 90-day window",
            "Mobile Number match within 90 days triggers transition to BM_Review",
        )
        broad = self._case(
            "TC150",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify transition from Dedup_Check to BM_Review when a duplicate PAN or mobile is found within 90 days",
            "System performs auto-deduplication check, detects a matching record, and triggers transition",
            "Lead moves to BM_Review state",
        )

        change = self.detector.detect_changes([generated], [specific, broad])[0]

        self.assertEqual(MODIFY, change.action)
        self.assertEqual("TC095", change.test_case_id)

    def test_close_duplicate_candidates_are_sent_to_review(self):
        generated = self._case(
            "GEN001",
            "Lead-to-Disbursement",
            "Verify that a mismatch between Karza OCR extracted name and the PAN name blocks the transition to Docs_Pending.",
            "1. Upload PAN image<br>2. System invokes Karza OCR<br>3. Mock OCR response to return a different name than on the PAN<br>4. Observe the outcome",
            "System displays a validation error indicating name mismatch and retains the lead in Eligibility state.",
        )
        candidate_one = self._case(
            "TC063",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify that a mismatch between OCR‑extracted name and PAN name blocks transition from Eligibility to Docs_Pending.",
            "1. Initiate bureau check<br>2. Mock API returns a score of 700 and OCR mismatch<br>3. System validates the response",
            "System prevents state transition, remains in Eligibility, and displays a validation message about name mismatch.",
        )
        candidate_two = self._case(
            "TC099",
            "Lead-to-Disbursement (L2D)",
            "Verify that a mismatch between Karza OCR name and PAN name prevents transition from Eligibility",
            "1. Trigger Initiate Bureau action<br>2. System receives a CIBIL score of 720<br>3. System receives Karza OCR name that does NOT match the name on the PAN<br>4. System validates name match rule<br>5. Observe outcome",
            "System rejects eligibility, remains in Eligibility state, and displays a name-mismatch validation message.",
        )

        change = self.detector.detect_changes(
            [generated], [candidate_one, candidate_two]
        )[0]

        self.assertEqual(REVIEW, change.action)
        self.assertIn("Multiple existing test cases", change.reason)

    def test_expected_result_that_needs_clarification_is_reviewed(self):
        generated = self._case(
            "GEN001",
            "Workflow",
            "Verify an undocumented outcome",
            "Perform the documented action",
            "Behavior is not explicitly specified in the requirement document and requires clarification.",
        )

        change = self.detector.detect_changes(
            [generated], []
        )[0]

        self.assertEqual(REVIEW, change.action)
        self.assertIn("needs clarification", change.reason)

    def test_matched_case_needing_clarification_is_reviewed_only_once(self):
        existing = self._case(
            "TC001",
            "Workflow",
            "Verify an undocumented outcome",
            "Perform the documented action",
            "Behavior is not explicitly specified in the requirement document and requires clarification.",
        )
        generated = self._case(
            "GEN001",
            "Workflow",
            "Verify an undocumented outcome",
            "Perform the documented action",
            "Behavior is not explicitly specified in the requirement document and requires clarification.",
        )

        changes = self.detector.detect_changes(
            [generated], [existing]
        )

        self.assertEqual([REVIEW], [change.action for change in changes])
        self.assertEqual("GEN001", changes[0].test_case_id)
        self.assertEqual("TC001", changes[0].existing_test_case.test_case_id)
        self.assertEqual(1, self.detector.summarize(changes)[REVIEW])

    def test_close_case_with_conflicting_rule_is_reviewed(self):
        generated = self._case(
            "GEN001",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify that a CIBIL score of 650 or lower prevents the lead from moving to Docs_Pending state.",
            "1. Initiate Bureau request<br>2. Mock the CIBIL API to return a score of 650 and consent_provided = true<br>3. Submit the response",
            "System blocks the transition and remains in Eligibility state because the CIBIL score must be greater than 650.",
        )
        existing = self._case(
            "TC087",
            "Lead-to-Disbursement (L2D) Pipeline",
            "Verify that a CIBIL score of exactly 650 prevents transition from Eligibility to Docs_Pending state.",
            "1. Trigger the Initiate Bureau action<br>2. Mock the CIBIL API response with score = 650, consent_provided = true<br>3. Submit the request",
            "System determines that the score does not satisfy the greater-than-650 rule, blocks the transition to Docs_Pending, and remains in Eligibility state.",
        )

        change = self.detector.detect_changes(
            [generated], [existing]
        )[0]

        self.assertEqual(REVIEW, change.action)
        self.assertIn("conflicting structured rule", change.reason)


def test_explicit_safe_retirement_preserves_history(tmp_path):
    detector = TestCaseChangeDetector()
    repository = RARETestCaseRepository(
        storage_path=str(tmp_path / "test_cases.json")
    )
    existing = TestCaseChangeDetectorRuleConflictTests._case(
        "TC001",
        "Food Delivery",
        "Verify delivery temperature is recorded",
        "Record the temperature at handoff",
        "The measured delivery temperature is saved.",
    )
    generated = TestCaseChangeDetectorRuleConflictTests._case(
        "GEN001",
        "Library Membership",
        "Verify borrowing renewal is available",
        "Open a member account and renew the current borrowing period",
        "The borrowing period is extended.",
    )
    repository.save(existing)

    incomplete = detector.detect_changes(
        [generated],
        repository.get_all(),
        generation_complete=False,
        retirement_candidates={"TC001"},
    )
    incomplete_summary = detector.summarize(incomplete)
    assert incomplete_summary[RETIRE] == 0
    assert incomplete_summary[REVIEW] == 1
    assert repository.count() == 1

    complete = detector.detect_changes(
        [generated],
        repository.get_all(),
        generation_complete=True,
        retirement_candidates={"TC001"},
    )
    complete_summary = detector.summarize(complete)
    assert complete_summary[ADD] == 1
    assert complete_summary[RETIRE] == 1
    assert complete_summary[REVIEW] == 0

    RARETestCaseVersionManager(repository=repository).apply_changes(complete)

    retired = repository.get_by_id("TC001")
    added = repository.get_by_id("TC002")
    assert retired is not None
    assert retired.version == 2
    assert retired.status == "RETIRED"
    assert added is not None
    assert added.version == 1
    assert added.status == "ACTIVE"
    assert repository.count() == 3
    assert len(repository.get_all()) == 2


def test_matching_active_case_is_preferred_over_retired_duplicate():
    detector = TestCaseChangeDetector()
    generated = TestCaseChangeDetectorRuleConflictTests._case(
        "GEN001",
        "Deduplication",
        "Verify duplicate record handling within 90 days",
        "Run the duplicate check and observe the resulting state",
        "A matching record routes the lead to manual review.",
    )
    retired = TestCaseChangeDetectorRuleConflictTests._case(
        "TC104",
        "Deduplication",
        "Verify duplicate record handling within 90 days",
        "Run the duplicate check and observe the resulting state",
        "A matching record routes the lead to manual review.",
    )
    retired.status = "RETIRED"
    active = TestCaseChangeDetectorRuleConflictTests._case(
        "TC150",
        "Deduplication",
        "Verify duplicate record handling within 90 days",
        "Run the duplicate check and observe the resulting state",
        "A matching record routes the lead to manual review.",
    )

    changes = detector.detect_changes([generated], [retired, active])

    assert changes[0].action == "KEEP"
    assert changes[0].test_case_id == "TC150"


def test_retired_only_identity_requires_review_instead_of_reactivation():
    detector = TestCaseChangeDetector()
    generated = TestCaseChangeDetectorRuleConflictTests._case(
        "GEN001",
        "Deduplication",
        "Verify duplicate record handling within 90 days",
        "Run the duplicate check and observe the resulting state",
        "A matching record routes the lead to manual review.",
    )
    retired = TestCaseChangeDetectorRuleConflictTests._case(
        "TC104",
        "Deduplication",
        "Verify duplicate record handling within 90 days",
        "Run the duplicate check and observe the resulting state",
        "A matching record routes the lead to manual review.",
    )
    retired.status = "RETIRED"

    change = detector.detect_changes([generated], [retired])[0]

    assert change.action == REVIEW
    assert change.test_case_id == "TC104"
    assert change.existing_test_case.status == "RETIRED"


if __name__ == "__main__":
    unittest.main()
