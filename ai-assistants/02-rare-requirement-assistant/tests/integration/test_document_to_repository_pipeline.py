from __future__ import annotations

from models.test_case import TestCase
from requirements.requirement_extractor import RequirementExtractor
from repository.requirement_repository import RequirementRepository
from repository.test_case_parser import TestCaseParser
from repository.test_case_repository import TestCaseRepository


def create_chunks(
    text: str,
    chunk_size: int = 7000,
    overlap: int = 600,
) -> list[str]:
    """
    Use the same chunking strategy currently used by RARE.

    This helper is intentionally kept inside the integration test
    because the current application keeps chunking inside app_phase5-backup.py.
    """

    if not text or not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be smaller than chunk size."
        )

    step = chunk_size - overlap

    chunks = []

    for start in range(
        0,
        len(text),
        step,
    ):
        chunk = text[
            start:start + chunk_size
        ]

        if chunk.strip():
            chunks.append(chunk)

    return chunks


def build_generated_test_output() -> str:
    """
    Deterministic replacement for the LLM-generated output.

    This represents the format produced by the existing
    TestGenerator and consumed by TestCaseParser.
    """

    return """| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GEN001 | Lead Management | Create a valid lead | Open lead screen.<br>Enter valid lead details.<br>Submit the lead. | Lead is created successfully. | P0 | Positive Case | Regression | UI Automation |
| GEN002 | Lead Management | Reject invalid mobile number | Open lead screen.<br>Enter an invalid mobile number.<br>Submit the lead. | Validation error is displayed and lead is not created. | P1 | Negative Case | Regression | UI Automation |
"""


def test_document_to_test_case_repository_pipeline(tmp_path):
    """
    Phase 14.1 integration test.

    Validates the implemented RARE component chain:

        Requirement Text
            -> Requirement Extraction
            -> Requirement Repository
            -> Document Chunking
            -> Generated Test Output
            -> Test Case Parsing
            -> Test Case Repository

    The LLM response is deterministic so the integration test
    does not depend on an external AI service.
    """

    # ------------------------------------------------------------
    # 1. Isolated repositories
    # ------------------------------------------------------------

    requirement_repository = RequirementRepository(
        storage_path=str(
            tmp_path / "requirements.json"
        )
    )

    test_case_repository = TestCaseRepository(
        storage_path=str(
            tmp_path / "test_cases.json"
        )
    )

    # ------------------------------------------------------------
    # 2. Requirement document
    # ------------------------------------------------------------

    document_text = """
    Lead Management System

    Requirement 1:
    The system must allow a user to create a valid lead
    using a valid mobile number.

    Requirement 2:
    The system must reject an invalid mobile number
    before creating the lead.
    """

    assert document_text.strip()

    # ------------------------------------------------------------
    # 3. Requirement Extraction
    # ------------------------------------------------------------

    requirement_extractor = RequirementExtractor()

    requirements = requirement_extractor.extract(
        document_text,
        source_document="integration_test_fsd.txt",
    )

    assert requirements
    assert len(requirements) >= 2

    # ------------------------------------------------------------
    # 4. Requirement Repository
    # ------------------------------------------------------------

    requirement_repository.save_many(
        requirements
    )

    stored_requirements = (
        requirement_repository.get_all()
    )

    assert len(stored_requirements) == len(
        requirements
    )

    assert all(
        requirement.requirement_id
        for requirement in stored_requirements
    )

    assert all(
        requirement.source_document
        == "integration_test_fsd.txt"
        for requirement in stored_requirements
    )

    # ------------------------------------------------------------
    # 5. Document Chunking
    # ------------------------------------------------------------

    chunks = create_chunks(
        document_text,
        chunk_size=7000,
        overlap=600,
    )

    assert chunks
    assert len(chunks) == 1
    assert document_text.strip() in chunks[0]

    # ------------------------------------------------------------
    # 6. Deterministic generated output
    # ------------------------------------------------------------

    generated_results = [
        build_generated_test_output()
        for _ in chunks
    ]

    assert len(generated_results) == len(
        chunks
    )

    assert all(
        result.strip()
        for result in generated_results
    )

    # ------------------------------------------------------------
    # 7. Test Case Parsing
    # ------------------------------------------------------------

    test_case_parser = TestCaseParser()

    parsed_cases = []

    for generated_result in generated_results:

        cases = test_case_parser.parse(
            generated_result,
            source_document="integration_test_fsd.txt",
        )

        parsed_cases.extend(cases)

    assert len(parsed_cases) == 2

    assert all(
        isinstance(test_case, TestCase)
        for test_case in parsed_cases
    )

    assert all(
        test_case.source_document
        == "integration_test_fsd.txt"
        for test_case in parsed_cases
    )

    # ------------------------------------------------------------
    # 8. Validate generated test case data
    # ------------------------------------------------------------

    test_case_ids = {
        test_case.test_case_id
        for test_case in parsed_cases
    }

    assert test_case_ids == {
        "GEN001",
        "GEN002",
    }

    scenarios = {
        test_case.scenario
        for test_case in parsed_cases
    }

    assert "Create a valid lead" in scenarios
    assert "Reject invalid mobile number" in scenarios

    # ------------------------------------------------------------
    # 9. Test Case Repository
    # ------------------------------------------------------------

    test_case_repository.save_many(
        parsed_cases
    )

    stored_test_cases = (
        test_case_repository.get_all()
    )

    assert len(stored_test_cases) == 2

    stored_ids = {
        test_case.test_case_id
        for test_case in stored_test_cases
    }

    assert stored_ids == {
        "GEN001",
        "GEN002",
    }

    # ------------------------------------------------------------
    # 10. Final integration assertions
    # ------------------------------------------------------------

    assert (
        requirement_repository.count()
        == len(requirements)
    )

    assert (
        test_case_repository.count()
        == 2
    )

    assert all(
        test_case.requirement_reference is None
        or isinstance(
            test_case.requirement_reference,
            str,
        )
        for test_case in stored_test_cases
    )

    print(
        "Phase 14.1 document-to-repository "
        "integration: PASS"
    )