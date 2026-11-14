import tempfile
import unittest
from pathlib import Path

from models.requirement import Requirement
from repository.requirement_change_detector import RequirementChangeDetector
from repository.requirement_version_manager import ADD, KEEP, MODIFY, RETIRE, REVIEW


def req(rid, text, module="General", priority="P1", kind="Functional", status="ACTIVE"):
    return Requirement(
        requirement_id=rid,
        module=module,
        requirement=text,
        requirement_type=kind,
        priority=priority,
        status=status,
    )


class RequirementChangeDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = RequirementChangeDetector()

    def actions(self, changes):
        return [change.action for change in changes]

    def test_exact_match_keeps_stable_repository_id_even_if_extractor_id_differs(self):
        old = req("REQ014", "The system must validate the submitted value.", "Validation")
        extracted = req("REQ001", "The system must validate the submitted value.", "Validation")
        changes = self.detector.detect_changes([extracted], [old])
        self.assertEqual([KEEP], self.actions(changes))
        self.assertEqual("REQ014", changes[0].requirement_id)

    def test_clear_wording_change_is_modify_and_preserves_existing_id(self):
        old = req("REQ014", "The system must validate the submitted value.", "Validation")
        extracted = req("REQ001", "The system must validate the submitted value before saving.", "Validation")
        changes = self.detector.detect_changes([extracted], [old])
        self.assertEqual([MODIFY], self.actions(changes))
        self.assertEqual("REQ014", changes[0].requirement_id)

    def test_new_requirement_is_add(self):
        extracted = req("REQ001", "The system must retain the submitted record.", "Records")
        changes = self.detector.detect_changes([extracted], [])
        self.assertEqual([ADD], self.actions(changes))

    def test_missing_requirement_is_review_when_generation_incomplete(self):
        old = req("REQ014", "The system must validate the submitted value.", "Validation")
        changes = self.detector.detect_changes([], [old], generation_complete=False)
        self.assertEqual([REVIEW], self.actions(changes))

    def test_missing_requirement_is_review_without_explicit_retirement_candidate(self):
        old = req("REQ014", "The system must validate the submitted value.", "Validation")
        changes = self.detector.detect_changes([], [old], generation_complete=True)
        self.assertEqual([REVIEW], self.actions(changes))

    def test_retirement_requires_complete_generation_and_explicit_candidate(self):
        old = req("REQ014", "The system must validate the submitted value.", "Validation")
        changes = self.detector.detect_changes(
            [], [old], generation_complete=True, retirement_candidates={"REQ014"}
        )
        self.assertEqual([RETIRE], self.actions(changes))

    def test_ambiguous_near_match_goes_to_review(self):
        old1 = req("REQ010", "The system must validate the submitted value before saving.", "Validation")
        old2 = req("REQ011", "The system must validate the submitted value before processing.", "Validation")
        extracted = req("REQ001", "The system must validate the submitted value before", "Validation")
        changes = self.detector.detect_changes([extracted], [old1, old2])
        self.assertIn(REVIEW, self.actions(changes))

    def test_duplicate_incoming_lines_go_to_review_not_duplicate_adds(self):
        one = req("REQ001", "The system must retain the submitted record.", "Records")
        two = req("REQ002", "The system must retain the submitted record.", "Records")
        changes = self.detector.detect_changes([one, two], [])
        self.assertEqual([REVIEW, REVIEW], self.actions(changes))

    def test_retired_requirement_match_goes_to_review(self):
        old = req("REQ014", "The system must validate the submitted value.", "Validation", status="RETIRED")
        extracted = req("REQ001", "The system must validate the submitted value.", "Validation")
        changes = self.detector.detect_changes([extracted], [old])
        self.assertEqual([REVIEW], self.actions(changes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
