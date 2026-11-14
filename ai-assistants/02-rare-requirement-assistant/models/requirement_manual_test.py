from datetime import datetime

from models.requirement import Requirement


def test_requirement_creation():
    requirement = Requirement(
        requirement_id="REQ001",
        module="Lead-to-Disbursement",
        requirement="Mobile number must contain exactly 10 digits.",
        requirement_type="Business Rule",
        priority="P1",
        source_document="BRD.docx",
        source_reference="Lead Creation",
    )

    assert requirement.requirement_id == "REQ001"
    assert requirement.module == "Lead-to-Disbursement"
    assert requirement.requirement == (
        "Mobile number must contain exactly 10 digits."
    )
    assert requirement.requirement_type == "Business Rule"
    assert requirement.priority == "P1"
    assert requirement.source_document == "BRD.docx"
    assert requirement.source_reference == "Lead Creation"
    assert requirement.version == 1
    assert requirement.status == "ACTIVE"

    print("Requirement creation: PASS")


def test_requirement_to_dict():
    requirement = Requirement(
        requirement_id="REQ002",
        module="Eligibility",
        requirement="CIBIL score must be greater than 650.",
        requirement_type="Business Rule",
        priority="P0",
        source_document="BRD.docx",
        source_reference="Eligibility",
    )

    data = requirement.to_dict()

    assert data["requirement_id"] == "REQ002"
    assert data["module"] == "Eligibility"
    assert data["requirement"] == (
        "CIBIL score must be greater than 650."
    )
    assert data["requirement_type"] == "Business Rule"
    assert data["priority"] == "P0"
    assert data["version"] == 1
    assert data["status"] == "ACTIVE"

    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)

    print("Requirement to_dict: PASS")


def test_requirement_from_dict():
    original = Requirement(
        requirement_id="REQ003",
        module="Underwriting",
        requirement="DTI must be less than 50%.",
        requirement_type="Business Rule",
        priority="P1",
        source_document="BRD.docx",
        source_reference="Underwriting",
    )

    data = original.to_dict()
    restored = Requirement.from_dict(data)

    assert restored.requirement_id == original.requirement_id
    assert restored.module == original.module
    assert restored.requirement == original.requirement
    assert restored.requirement_type == original.requirement_type
    assert restored.priority == original.priority
    assert restored.source_document == original.source_document
    assert restored.source_reference == original.source_reference
    assert restored.version == original.version
    assert restored.status == original.status

    assert isinstance(restored.created_at, datetime)
    assert isinstance(restored.updated_at, datetime)

    print("Requirement from_dict: PASS")


def test_requirement_versioning():
    requirement = Requirement(
        requirement_id="REQ004",
        module="Document Collection",
        requirement="Self-employed applicants must upload GST Returns.",
        requirement_type="Business Rule",
        priority="P1",
        source_document="BRD.docx",
        source_reference="Document Matrix",
    )

    new_version = requirement.create_new_version(
        requirement=(
            "Self-employed applicants must upload GST Returns "
            "before proceeding to Underwriting."
        )
    )

    assert new_version.requirement_id == "REQ004"
    assert new_version.version == 2
    assert new_version.status == "ACTIVE"
    assert new_version.module == requirement.module
    assert new_version.requirement_type == requirement.requirement_type
    assert new_version.priority == requirement.priority

    assert new_version.requirement != requirement.requirement
    assert new_version.created_at == requirement.created_at
    assert new_version.updated_at >= requirement.updated_at

    print("Requirement versioning: PASS")


def test_requirement_retire():
    requirement = Requirement(
        requirement_id="REQ005",
        module="Lead Creation",
        requirement="Product type is mandatory.",
        requirement_type="Business Rule",
        priority="P1",
    )

    retired = requirement.retire()

    assert retired.requirement_id == "REQ005"
    assert retired.version == 2
    assert retired.status == "RETIRED"
    assert retired.requirement == requirement.requirement

    print("Requirement retire: PASS")


def test_requirement_activate():
    requirement = Requirement(
        requirement_id="REQ006",
        module="Lead Creation",
        requirement="Mobile number is mandatory.",
        requirement_type="Business Rule",
        priority="P1",
        status="RETIRED",
    )

    activated = requirement.activate()

    assert activated.requirement_id == "REQ006"
    assert activated.version == 2
    assert activated.status == "ACTIVE"
    assert activated.requirement == requirement.requirement

    print("Requirement activate: PASS")


def test_requirement_review():
    requirement = Requirement(
        requirement_id="REQ007",
        module="Credit Bureau",
        requirement="Behavior for missing PAN requires clarification.",
        requirement_type="Open Question",
        priority="P2",
    )

    review = requirement.review()

    assert review.requirement_id == "REQ007"
    assert review.version == 2
    assert review.status == "REVIEW"
    assert review.requirement == requirement.requirement

    print("Requirement review: PASS")


def run_all_tests():
    print("=" * 60)
    print("REQUIREMENT MODEL MANUAL TEST")
    print("=" * 60)

    test_requirement_creation()
    test_requirement_to_dict()
    test_requirement_from_dict()
    test_requirement_versioning()
    test_requirement_retire()
    test_requirement_activate()
    test_requirement_review()

    print("=" * 60)
    print("All Requirement model tests completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()