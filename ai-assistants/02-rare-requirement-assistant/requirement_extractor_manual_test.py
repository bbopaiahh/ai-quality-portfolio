from requirements.requirement_extractor import RequirementExtractor


def test_empty_input():
    extractor = RequirementExtractor()

    requirements = extractor.extract("")

    assert requirements == []

    print("Empty input: PASS")


def test_single_requirement():
    extractor = RequirementExtractor()

    content = """
Module: Lead Creation

Mobile number must contain exactly 10 digits.
"""

    requirements = extractor.extract(
        content,
        source_document="BRD.docx",
    )

    assert len(requirements) == 1

    requirement = requirements[0]

    assert requirement.requirement_id == "REQ001"
    assert requirement.module == "Lead Creation"
    assert requirement.requirement == (
        "Mobile number must contain exactly 10 digits."
    )
    assert requirement.requirement_type == "Business Rule"
    assert requirement.priority == "P0"
    assert requirement.source_document == "BRD.docx"

    print("Single requirement extraction: PASS")


def test_multiple_requirements():
    extractor = RequirementExtractor()

    content = """
Module: Lead Creation

Mobile number must contain exactly 10 digits.

Module: Eligibility

CIBIL score must be greater than 650.

Module: Underwriting

DTI must be less than 50%.
"""

    requirements = extractor.extract(
        content,
        source_document="BRD.docx",
    )

    assert len(requirements) == 3

    assert requirements[0].requirement_id == "REQ001"
    assert requirements[1].requirement_id == "REQ002"
    assert requirements[2].requirement_id == "REQ003"

    assert requirements[0].module == "Lead Creation"
    assert requirements[1].module == "Eligibility"
    assert requirements[2].module == "Underwriting"

    print("Multiple requirements extraction: PASS")


def test_requirement_type_classification():
    extractor = RequirementExtractor()

    content = """
Module: Security

PAN data must be encrypted using AES-256.

Module: Credit Bureau API

The API must return HTTP 200 for a successful request.

Module: Lead Search

Search results must be displayed within 1.8 seconds.
"""

    requirements = extractor.extract(
        content,
        source_document="BRD.docx",
    )

    assert len(requirements) == 3

    assert requirements[0].requirement_type == "Security"
    assert requirements[1].requirement_type == "API"
    assert requirements[2].requirement_type == "Performance"

    print("Requirement type classification: PASS")


def test_priority_classification():
    extractor = RequirementExtractor()

    content = """
Module: Authentication

Authentication is mandatory for all authorized users.

Module: Validation

The system should display a validation message.

Module: Edge Case

The boundary condition should be handled correctly.
"""

    requirements = extractor.extract(
        content,
        source_document="BRD.docx",
    )

    assert len(requirements) == 3

    assert requirements[0].priority == "P0"
    assert requirements[1].priority == "P1"
    assert requirements[2].priority == "P2"

    print("Priority classification: PASS")


def test_source_information():
    extractor = RequirementExtractor()

    content = """
Module: Document Collection

Self-employed applicants must upload GST Returns.
"""

    requirements = extractor.extract(
        content,
        source_document="Loan_BRDR_v2.docx",
    )

    assert len(requirements) == 1

    requirement = requirements[0]

    assert requirement.source_document == "Loan_BRDR_v2.docx"
    assert requirement.source_reference == "Document Collection"

    print("Source information: PASS")


def test_non_requirement_text_is_ignored():
    extractor = RequirementExtractor()

    content = """
Module: General Information

This document describes the loan application workflow.

The application contains several screens.

Users can navigate between the screens.

Module: Lead Creation

The mobile number must contain exactly 10 digits.
"""

    requirements = extractor.extract(
        content,
        source_document="BRD.docx",
    )

    assert len(requirements) == 1

    assert requirements[0].requirement_id == "REQ001"
    assert requirements[0].module == "Lead Creation"

    print("Non-requirement text filtering: PASS")


def test_requirement_ids_reset_for_new_extraction():
    extractor = RequirementExtractor()

    first_content = """
Module: Lead Creation

Mobile number must contain exactly 10 digits.
"""

    second_content = """
Module: Eligibility

CIBIL score must be greater than 650.
"""

    first_result = extractor.extract(
        first_content,
        source_document="BRD.docx",
    )

    second_result = extractor.extract(
        second_content,
        source_document="BRD_v2.docx",
    )

    assert first_result[0].requirement_id == "REQ001"
    assert second_result[0].requirement_id == "REQ001"

    print("Requirement ID reset: PASS")


def run_all_tests():
    print("=" * 60)
    print("REQUIREMENT EXTRACTOR MANUAL TEST")
    print("=" * 60)

    test_empty_input()
    test_single_requirement()
    test_multiple_requirements()
    test_requirement_type_classification()
    test_priority_classification()
    test_source_information()
    test_non_requirement_text_is_ignored()
    test_requirement_ids_reset_for_new_extraction()

    print("=" * 60)
    print("All Requirement Extractor tests completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()