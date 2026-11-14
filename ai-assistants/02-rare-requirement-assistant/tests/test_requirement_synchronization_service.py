import tempfile
import unittest
from pathlib import Path

from models.requirement import Requirement
from repository.requirement_repository import RequirementRepository
from repository.requirement_synchronization_service import RequirementSynchronizationService


def req(text, module="General", rid="REQ001", priority="P2", req_type="Functional"):
    return Requirement(
        requirement_id=rid,
        module=module,
        requirement=text,
        requirement_type=req_type,
        priority=priority,
        source_document="sample.docx",
        source_reference=module,
    )


class RequirementSynchronizationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = RequirementRepository(
            storage_path=str(Path(self.temp_dir.name) / "requirements.json")
        )
        self.service = RequirementSynchronizationService(repository=self.repository)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_sync_adds_requirement_with_managed_id(self):
        report = self.service.synchronize([
            req("The system must validate the submitted record.")
        ])
        self.assertEqual(report.counts["ADD"], 1)
        self.assertEqual(len(report.affected_requirements), 1)
        self.assertEqual(report.affected_requirements[0].requirement_id, "REQ001")
        self.assertEqual(report.affected_requirements[0].version, 1)

    def test_exact_match_keeps_existing_id_and_version(self):
        self.repository.save(req("The system must validate the submitted record.", rid="REQ009"))
        report = self.service.synchronize([
            req("The system must validate the submitted record.", rid="REQ001")
        ])
        self.assertEqual(report.counts["KEEP"], 1)
        self.assertEqual(report.affected_requirements[0].requirement_id, "REQ009")
        self.assertEqual(report.affected_requirements[0].version, 1)

    def test_clear_modification_creates_next_version_and_preserves_id(self):
        self.repository.save(req("The system must validate the submitted record.", rid="REQ009"))
        report = self.service.synchronize([
            req("The system must validate the submitted record before saving.", rid="REQ001")
        ])
        latest = self.repository.get_by_id("REQ009")
        self.assertEqual(report.counts["MODIFY"], 1)
        self.assertEqual(latest.requirement_id, "REQ009")
        self.assertEqual(latest.version, 2)
        self.assertIn("before saving", latest.requirement)

    def test_missing_requirement_is_review_and_not_retired(self):
        original = req("The system must validate the submitted record.", rid="REQ009")
        self.repository.save(original)
        report = self.service.synchronize([
            req("Users can export archived reports as CSV.", rid="REQ001")
        ], generation_complete=False)
        latest = self.repository.get_by_id("REQ009")
        self.assertGreaterEqual(report.counts["REVIEW"], 1)
        self.assertEqual(latest.status, "ACTIVE")
        self.assertEqual(latest.version, 1)

    def test_empty_extraction_does_not_change_repository(self):
        self.repository.save(req("The system must validate the submitted record.", rid="REQ009"))
        report = self.service.synchronize([])
        self.assertEqual(report.proposed_changes, [])
        self.assertEqual(self.repository.get_by_id("REQ009").version, 1)


if __name__ == "__main__":
    unittest.main()
