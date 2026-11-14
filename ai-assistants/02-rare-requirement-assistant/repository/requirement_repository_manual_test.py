from pathlib import Path
from tempfile import TemporaryDirectory

from models.requirement import Requirement
from repository.requirement_repository import RequirementRepository


def create_requirement(
    requirement_id: str,
    module: str,
    requirement: str,
    requirement_type: str = "Functional",
    priority: str = "P2",
) -> Requirement:
    return Requirement(
        requirement_id=requirement_id,
        module=module,
        requirement=requirement,
        requirement_type=requirement_type,
        priority=priority,
        source_document="sample_brd.txt",
        source_reference=module,
    )


def main():
    print("=" * 60)
    print("REQUIREMENT REPOSITORY MANUAL TEST")
    print("=" * 60)

    with TemporaryDirectory() as temp_dir:
        storage_path = (
            Path(temp_dir)
            / "requirement_repository.json"
        )

        repository = RequirementRepository(
            storage_path=str(storage_path)
        )

        # --------------------------------------------------
        # Test 1: Empty repository
        # --------------------------------------------------

        assert repository.count() == 0
        assert repository.active_count() == 0

        print("Empty repository: PASS")

        # --------------------------------------------------
        # Test 2: Save single requirement
        # --------------------------------------------------

        requirement_1 = create_requirement(
            requirement_id="REQ001",
            module="Lead Creation",
            requirement=(
                "The system must create a lead "
                "with valid mandatory fields."
            ),
            requirement_type="Business Rule",
            priority="P0",
        )

        saved = repository.save(requirement_1)

        assert saved.requirement_id == "REQ001"
        assert repository.count() == 1

        print("Save requirement: PASS")

        # --------------------------------------------------
        # Test 3: Get by ID
        # --------------------------------------------------

        fetched = repository.get_by_id("REQ001")

        assert fetched is not None
        assert fetched.requirement_id == "REQ001"
        assert fetched.module == "Lead Creation"

        print("Get by ID: PASS")

        # --------------------------------------------------
        # Test 4: Save multiple requirements
        # --------------------------------------------------

        requirement_2 = create_requirement(
            requirement_id="REQ002",
            module="Eligibility",
            requirement=(
                "The system must reject the application "
                "when CIBIL is below 650."
            ),
            requirement_type="Business Rule",
            priority="P0",
        )

        requirement_3 = create_requirement(
            requirement_id="REQ003",
            module="Document Checklist",
            requirement=(
                "PAN and Aadhaar documents are mandatory."
            ),
            requirement_type="Functional",
            priority="P1",
        )

        saved_many = repository.save_many(
            [
                requirement_2,
                requirement_3,
            ]
        )

        assert len(saved_many) == 2
        assert repository.count() == 3

        print("Save multiple requirements: PASS")

        # --------------------------------------------------
        # Test 5: Get all latest requirements
        # --------------------------------------------------

        all_requirements = repository.get_all()

        assert len(all_requirements) == 3

        requirement_ids = {
            requirement.requirement_id
            for requirement in all_requirements
        }

        assert requirement_ids == {
            "REQ001",
            "REQ002",
            "REQ003",
        }

        print("Get all requirements: PASS")

        # --------------------------------------------------
        # Test 6: Search
        # --------------------------------------------------

        search_results = repository.search("CIBIL")

        assert len(search_results) == 1
        assert (
            search_results[0].requirement_id
            == "REQ002"
        )

        print("Search requirements: PASS")

        # --------------------------------------------------
        # Test 7: Duplicate ID protection
        # --------------------------------------------------

        duplicate = create_requirement(
            requirement_id="REQ001",
            module="Duplicate",
            requirement="Duplicate requirement.",
        )

        try:
            repository.save(duplicate)

            raise AssertionError(
                "Duplicate Requirement ID was accepted."
            )

        except ValueError:
            pass

        assert repository.count() == 3

        print("Duplicate ID protection: PASS")

        # --------------------------------------------------
        # Test 8: Requirement versioning
        # --------------------------------------------------

        existing = repository.get_by_id("REQ001")

        assert existing is not None
        assert existing.version == 1

        new_version = existing.create_new_version(
            requirement=(
                "The system must create a lead only "
                "when all mandatory fields are valid."
            ),
            priority="P1",
        )

        assert new_version.requirement_id == "REQ001"
        assert new_version.version == 2
        assert new_version.status == "ACTIVE"

        repository.save_version(new_version)

        latest = repository.get_by_id("REQ001")

        assert latest is not None
        assert latest.version == 2
        assert latest.priority == "P1"

        print("Requirement versioning: PASS")

        # --------------------------------------------------
        # Test 9: History
        # --------------------------------------------------

        history = repository.get_history("REQ001")

        assert len(history) == 2
        assert history[0].version == 1
        assert history[1].version == 2

        print("Requirement history: PASS")

        # --------------------------------------------------
        # Test 10: Latest-only get_all
        # --------------------------------------------------

        all_latest = repository.get_all()

        assert len(all_latest) == 3

        req001_versions = [
            requirement.version
            for requirement in all_latest
            if requirement.requirement_id == "REQ001"
        ]

        assert req001_versions == [2]

        print("Latest version filtering: PASS")

        # --------------------------------------------------
        # Test 11: Active count
        # --------------------------------------------------

        assert repository.active_count() == 3

        print("Active requirement count: PASS")

        # --------------------------------------------------
        # Test 12: Versioning second requirement
        # --------------------------------------------------

        req002 = repository.get_by_id("REQ002")

        assert req002 is not None
        assert req002.version == 1

        updated_req002 = req002.create_new_version(
            priority="P1",
        )

        repository.save_version(updated_req002)

        latest_req002 = repository.get_by_id("REQ002")

        assert latest_req002 is not None
        assert latest_req002.version == 2
        assert latest_req002.priority == "P1"

        print("Second requirement versioning: PASS")

        # --------------------------------------------------
        # Test 13: Retire requirement
        # --------------------------------------------------

        req003 = repository.get_by_id("REQ003")

        assert req003 is not None
        assert req003.version == 1

        retired_req003 = req003.retire()

        repository.save_version(retired_req003)

        latest_req003 = repository.get_by_id("REQ003")

        assert latest_req003 is not None
        assert latest_req003.version == 2
        assert latest_req003.status == "RETIRED"

        print("Requirement retirement: PASS")

        # --------------------------------------------------
        # Test 14: Active count after retirement
        # --------------------------------------------------

        assert repository.active_count() == 2

        print("Active count after retirement: PASS")

        # --------------------------------------------------
        # Test 15: Delete requirement
        # --------------------------------------------------

        deleted = repository.delete("REQ003")

        assert deleted is True
        assert repository.get_by_id("REQ003") is None

        # REQ001 has 2 versions
        # REQ002 has 2 versions
        # REQ003 was deleted completely
        assert repository.count() == 4

        print("Delete requirement: PASS")

        # --------------------------------------------------
        # Test 16: Delete non-existing requirement
        # --------------------------------------------------

        deleted_missing = repository.delete(
            "REQ999"
        )

        assert deleted_missing is False

        print("Delete missing requirement: PASS")

        # --------------------------------------------------
        # Test 17: Clear repository
        # --------------------------------------------------

        repository.clear()

        assert repository.count() == 0
        assert repository.get_all() == []
        assert repository.active_count() == 0

        print("Clear repository: PASS")

        # --------------------------------------------------
        # Final verification
        # --------------------------------------------------

        assert storage_path.exists()

        print("Repository storage file: PASS")

    print("=" * 60)
    print(
        "All Requirement Repository tests completed successfully."
    )
    print("=" * 60)


if __name__ == "__main__":
    main()