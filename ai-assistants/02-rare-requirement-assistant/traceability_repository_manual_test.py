from pathlib import Path
from tempfile import TemporaryDirectory

from models.traceability import Traceability
from repository.traceability_repository import (
    TraceabilityRepository,
)


def create_traceability(
    requirement_id: str,
    test_case_id: str,
    relationship_type: str = "COVERED",
    status: str = "ACTIVE",
) -> Traceability:
    return Traceability(
        requirement_id=requirement_id,
        test_case_id=test_case_id,
        relationship_type=relationship_type,
        status=status,
    )


def main():
    print("=" * 60)
    print("TRACEABILITY REPOSITORY MANUAL TEST")
    print("=" * 60)

    with TemporaryDirectory() as temp_dir:
        storage_path = (
            Path(temp_dir)
            / "traceability_repository.json"
        )

        repository = TraceabilityRepository(
            storage_path=str(storage_path)
        )

        # --------------------------------------------------
        # Test 1: Empty repository
        # --------------------------------------------------

        assert repository.count() == 0
        assert repository.get_all() == []

        print("Empty repository: PASS")

        # --------------------------------------------------
        # Test 2: Save single mapping
        # --------------------------------------------------

        mapping_1 = create_traceability(
            requirement_id="REQ001",
            test_case_id="TC001",
        )

        saved = repository.save(mapping_1)

        assert saved.requirement_id == "REQ001"
        assert saved.test_case_id == "TC001"
        assert repository.count() == 1

        print("Save traceability mapping: PASS")

        # --------------------------------------------------
        # Test 3: Get all mappings
        # --------------------------------------------------

        all_mappings = repository.get_all()

        assert len(all_mappings) == 1
        assert (
            all_mappings[0].requirement_id
            == "REQ001"
        )
        assert (
            all_mappings[0].test_case_id
            == "TC001"
        )

        print("Get all mappings: PASS")

        # --------------------------------------------------
        # Test 4: Get by requirement
        # --------------------------------------------------

        mapping_2 = create_traceability(
            requirement_id="REQ001",
            test_case_id="TC002",
        )

        repository.save(mapping_2)

        requirement_mappings = (
            repository.get_by_requirement("REQ001")
        )

        assert len(requirement_mappings) == 2

        test_case_ids = {
            mapping.test_case_id
            for mapping in requirement_mappings
        }

        assert test_case_ids == {
            "TC001",
            "TC002",
        }

        print("Get by requirement: PASS")

        # --------------------------------------------------
        # Test 5: Get by test case
        # --------------------------------------------------

        test_case_mappings = (
            repository.get_by_test_case("TC001")
        )

        assert len(test_case_mappings) == 1
        assert (
            test_case_mappings[0].requirement_id
            == "REQ001"
        )

        print("Get by test case: PASS")

        # --------------------------------------------------
        # Test 6: Get specific mapping
        # --------------------------------------------------

        mapping = repository.get_mapping(
            requirement_id="REQ001",
            test_case_id="TC002",
        )

        assert mapping is not None
        assert mapping.requirement_id == "REQ001"
        assert mapping.test_case_id == "TC002"

        print("Get specific mapping: PASS")

        # --------------------------------------------------
        # Test 7: Missing mapping
        # --------------------------------------------------

        missing_mapping = repository.get_mapping(
            requirement_id="REQ999",
            test_case_id="TC999",
        )

        assert missing_mapping is None

        print("Missing mapping handling: PASS")

        # --------------------------------------------------
        # Test 8: Save multiple mappings
        # --------------------------------------------------

        mapping_3 = create_traceability(
            requirement_id="REQ002",
            test_case_id="TC003",
        )

        mapping_4 = create_traceability(
            requirement_id="REQ003",
            test_case_id="TC004",
        )

        saved_many = repository.save_many(
            [
                mapping_3,
                mapping_4,
            ]
        )

        assert len(saved_many) == 2
        assert repository.count() == 4

        print("Save multiple mappings: PASS")

        # --------------------------------------------------
        # Test 9: Duplicate protection
        # --------------------------------------------------

        duplicate = create_traceability(
            requirement_id="REQ001",
            test_case_id="TC001",
        )

        try:
            repository.save(duplicate)

            raise AssertionError(
                "Duplicate traceability mapping "
                "was accepted."
            )

        except ValueError:
            pass

        assert repository.count() == 4

        print("Duplicate mapping protection: PASS")

        # --------------------------------------------------
        # Test 10: Search by Requirement ID
        # --------------------------------------------------

        search_results = repository.search("REQ002")

        assert len(search_results) == 1
        assert (
            search_results[0].test_case_id
            == "TC003"
        )

        print("Search by requirement: PASS")

        # --------------------------------------------------
        # Test 11: Search by Test Case ID
        # --------------------------------------------------

        search_results = repository.search("TC004")

        assert len(search_results) == 1
        assert (
            search_results[0].requirement_id
            == "REQ003"
        )

        print("Search by test case: PASS")

        # --------------------------------------------------
        # Test 12: Search by relationship type
        # --------------------------------------------------

        search_results = repository.search(
            "COVERED"
        )

        assert len(search_results) == 4

        print("Search by relationship type: PASS")

        # --------------------------------------------------
        # Test 13: Update mapping
        # --------------------------------------------------

        existing = repository.get_mapping(
            requirement_id="REQ003",
            test_case_id="TC004",
        )

        assert existing is not None
        assert existing.status == "ACTIVE"

        updated = Traceability(
            requirement_id="REQ003",
            test_case_id="TC004",
            relationship_type="COVERED",
            status="REVIEW",
        )

        repository.update(updated)

        latest = repository.get_mapping(
            requirement_id="REQ003",
            test_case_id="TC004",
        )

        assert latest is not None
        assert latest.status == "REVIEW"

        print("Update mapping: PASS")

        # --------------------------------------------------
        # Test 14: Delete specific mapping
        # --------------------------------------------------

        deleted = repository.delete(
            requirement_id="REQ003",
            test_case_id="TC004",
        )

        assert deleted is True
        assert (
            repository.get_mapping(
                "REQ003",
                "TC004",
            )
            is None
        )

        assert repository.count() == 3

        print("Delete specific mapping: PASS")

        # --------------------------------------------------
        # Test 15: Delete missing mapping
        # --------------------------------------------------

        deleted_missing = repository.delete(
            requirement_id="REQ999",
            test_case_id="TC999",
        )

        assert deleted_missing is False

        print("Delete missing mapping: PASS")

        # --------------------------------------------------
        # Test 16: Delete by requirement
        # --------------------------------------------------

        mapping_5 = create_traceability(
            requirement_id="REQ004",
            test_case_id="TC005",
        )

        mapping_6 = create_traceability(
            requirement_id="REQ004",
            test_case_id="TC006",
        )

        repository.save_many(
            [
                mapping_5,
                mapping_6,
            ]
        )

        deleted_count = (
            repository.delete_by_requirement(
                "REQ004"
            )
        )

        assert deleted_count == 2
        assert repository.count() == 3
        assert (
            repository.get_by_requirement("REQ004")
            == []
        )

        print("Delete by requirement: PASS")

        # --------------------------------------------------
        # Test 17: Delete by test case
        # --------------------------------------------------

        mapping_7 = create_traceability(
            requirement_id="REQ005",
            test_case_id="TC007",
        )

        mapping_8 = create_traceability(
            requirement_id="REQ006",
            test_case_id="TC007",
        )

        repository.save_many(
            [
                mapping_7,
                mapping_8,
            ]
        )

        deleted_count = (
            repository.delete_by_test_case(
                "TC007"
            )
        )

        assert deleted_count == 2
        assert repository.count() == 3
        assert (
            repository.get_by_test_case("TC007")
            == []
        )

        print("Delete by test case: PASS")

        # --------------------------------------------------
        # Test 18: Clear repository
        # --------------------------------------------------

        repository.clear()

        assert repository.count() == 0
        assert repository.get_all() == []

        print("Clear repository: PASS")

        # --------------------------------------------------
        # Test 19: Storage file
        # --------------------------------------------------

        assert storage_path.exists()

        print("Repository storage file: PASS")

    print("=" * 60)
    print(
        "All Traceability Repository tests completed successfully."
    )
    print("=" * 60)


if __name__ == "__main__":
    main()