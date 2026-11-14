from pathlib import Path
from tempfile import TemporaryDirectory

from models.requirement import Requirement
from repository.requirement_repository import RequirementRepository
from repository.requirement_version_manager import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    REVIEW,
    RequirementChange,
    RequirementVersionManager,
)


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
    print("REQUIREMENT VERSION MANAGER MANUAL TEST")
    print("=" * 60)

    with TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "requirement_repository.json"

        repository = RequirementRepository(
            storage_path=str(storage_path)
        )

        manager = RequirementVersionManager(
            repository=repository
        )

        # ========================================================
        # 1. Create initial repository
        # ========================================================

        print("1. Creating initial repository...")

        initial_requirements = [
            create_requirement(
                "REQ001",
                "Lead Creation",
                "The system must create a valid lead.",
                "Business Rule",
                "P0",
            ),
            create_requirement(
                "REQ002",
                "Eligibility",
                "The system must validate CIBIL.",
                "Business Rule",
                "P0",
            ),
            create_requirement(
                "REQ003",
                "Documents",
                "Mandatory documents must be validated.",
                "Functional",
                "P1",
            ),
            create_requirement(
                "REQ004",
                "Underwriting",
                "DTI must be validated.",
                "Business Rule",
                "P1",
            ),
        ]

        repository.save_many(initial_requirements)

        assert repository.count() == 4

        print(
            "Initial repository count:",
            repository.count(),
        )

        # ========================================================
        # 2. Prepare detected changes
        # ========================================================

        print("\n2. Creating detected changes...")

        existing_req001 = repository.get_by_id("REQ001")
        existing_req002 = repository.get_by_id("REQ002")
        existing_req003 = repository.get_by_id("REQ003")
        existing_req004 = repository.get_by_id("REQ004")

        assert existing_req001 is not None
        assert existing_req002 is not None
        assert existing_req003 is not None
        assert existing_req004 is not None

        changes = [
            # KEEP
            RequirementChange(
                action=KEEP,
                requirement_id="REQ001",
                new_requirement=existing_req001,
                existing_requirement=existing_req001,
                reason="No changes.",
            ),

            # MODIFY
            RequirementChange(
                action=MODIFY,
                requirement_id="REQ002",
                new_requirement=create_requirement(
                    "REQ999",
                    "Eligibility",
                    "The system must validate CIBIL and reject "
                    "applications below the required score.",
                    "Business Rule",
                    "P1",
                ),
                existing_requirement=existing_req002,
                reason="Requirement wording and priority changed.",
            ),

            # RETIRE
            RequirementChange(
                action=RETIRE,
                requirement_id="REQ003",
                new_requirement=None,
                existing_requirement=existing_req003,
                reason="Requirement is no longer applicable.",
            ),

            # ADD
            RequirementChange(
                action=ADD,
                requirement_id=None,
                new_requirement=create_requirement(
                    "REQ001",
                    "Document Checklist",
                    "The system must validate income documents.",
                    "Business Rule",
                    "P1",
                ),
                existing_requirement=None,
                reason="New requirement.",
            ),

            # REVIEW
            RequirementChange(
                action=REVIEW,
                requirement_id="REQ004",
                new_requirement=None,
                existing_requirement=existing_req004,
                reason="Insufficient evidence for automatic change.",
            ),
        ]

        print(
            "Changes prepared:",
            len(changes),
        )

        # ========================================================
        # 3. Apply version management
        # ========================================================

        print(
            "\n3. Applying requirement version management..."
        )

        affected_requirements = manager.apply_changes(
            changes
        )

        # KEEP, MODIFY, RETIRE and ADD are affected.
        # REVIEW is intentionally a no-op.
        assert len(affected_requirements) == 4

        print(
            "Affected requirements:",
            len(affected_requirements),
        )

        # ========================================================
        # 4. Verify KEEP
        # ========================================================

        print("\n4. Verifying KEEP...")

        req001 = repository.get_by_id("REQ001")

        assert req001 is not None
        assert req001.version == 1
        assert req001.status == "ACTIVE"

        print(
            f"REQ001 | v{req001.version} | "
            f"{req001.status}"
        )

        # ========================================================
        # 5. Verify MODIFY
        # ========================================================

        print("\n5. Verifying MODIFY...")

        req002 = repository.get_by_id("REQ002")

        assert req002 is not None
        assert req002.version == 2
        assert req002.status == "ACTIVE"
        assert "reject applications" in req002.requirement
        assert req002.priority == "P1"

        print(
            f"REQ002 | v{req002.version} | "
            f"{req002.status} | {req002.priority}"
        )

        # ========================================================
        # 6. Verify RETIRE
        # ========================================================

        print("\n6. Verifying RETIRE...")

        req003 = repository.get_by_id("REQ003")

        assert req003 is not None
        assert req003.version == 2
        assert req003.status == "RETIRED"

        print(
            f"REQ003 | v{req003.version} | "
            f"{req003.status}"
        )

        # ========================================================
        # 7. Verify ADD
        # ========================================================

        print("\n7. Verifying ADD...")

        req005 = repository.get_by_id("REQ005")

        assert req005 is not None
        assert req005.version == 1
        assert req005.status == "ACTIVE"
        assert req005.module == "Document Checklist"

        print(
            f"REQ005 | v{req005.version} | "
            f"{req005.status} | {req005.module}"
        )

        # ========================================================
        # 8. Verify REVIEW is a safe no-op
        # ========================================================

        print("\n8. Verifying REVIEW...")

        req004 = repository.get_by_id("REQ004")

        assert req004 is not None
        assert req004.version == 1
        assert req004.status == "ACTIVE"

        req004_history = repository.get_history("REQ004")

        assert len(req004_history) == 1
        assert req004_history[0].version == 1

        print(
            f"REQ004 | v{req004.version} | "
            f"{req004.status} | REVIEW unchanged"
        )

        # ========================================================
        # 9. Verify history
        # ========================================================

        print("\n9. Verifying repository history...")

        req002_history = repository.get_history("REQ002")
        req003_history = repository.get_history("REQ003")

        assert len(req002_history) == 2
        assert req002_history[0].version == 1
        assert req002_history[1].version == 2

        assert len(req003_history) == 2
        assert req003_history[0].version == 1
        assert req003_history[1].version == 2
        assert req003_history[1].status == "RETIRED"

        print(
            "REQ002 stored versions:",
            len(req002_history),
        )

        print(
            "REQ003 stored versions:",
            len(req003_history),
        )

        # ========================================================
        # 10. Verify latest-only repository view
        # ========================================================

        print(
            "\n10. Verifying latest repository view..."
        )

        latest_requirements = repository.get_all()

        assert len(latest_requirements) == 5

        latest_versions = {
            requirement.requirement_id: requirement.version
            for requirement in latest_requirements
        }

        assert latest_versions == {
            "REQ001": 1,
            "REQ002": 2,
            "REQ003": 2,
            "REQ004": 1,
            "REQ005": 1,
        }

        print(
            "Latest requirements:",
            len(latest_requirements),
        )

        # ========================================================
        # 11. Verify active count
        # ========================================================

        print("\n11. Verifying active count...")

        assert repository.active_count() == 4

        print(
            "Active requirements:",
            repository.active_count(),
        )

        # ========================================================
        # 12. Final state
        # ========================================================

        print("\n12. Final repository state...")

        for requirement in sorted(
            latest_requirements,
            key=lambda item: item.requirement_id,
        ):
            print(
                f"{requirement.requirement_id} | "
                f"v{requirement.version} | "
                f"{requirement.status} | "
                f"{requirement.requirement}"
            )

    print("=" * 60)
    print(
        "All Requirement Version Manager tests "
        "completed successfully."
    )
    print("=" * 60)


if __name__ == "__main__":
    main()