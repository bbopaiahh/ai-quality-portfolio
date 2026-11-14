from types import SimpleNamespace

from generation.test_generator import TestGenerator as Generator
from repository.test_case_parser import TestCaseParser as CaseParser
from traceability.mapping_builder import build_requirement_test_case_mappings


class StubLLMClient:
    def generate(self, prompt: str) -> str:
        return """| Test Case ID | Module | Scenario | Pre Condition | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|---|
| GEN001 | Account Services | Validate a submitted record | A record is ready | 1. Enter the record.<br>2. Submit it. | The result is pass \\| fallback. | P1 | Positive Case | Regression | UI Automation |

| Legend | Meaning |
| A | Extra model commentary |
"""


class SequenceLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def test_generator_returns_only_validated_table_rows_and_preserves_escaped_pipes():
    generator = Generator(llm_client=StubLLMClient())

    output = generator.generate_from_chunk("Any business requirement text")
    parsed = CaseParser().parse(output, source_document="sample.docx")

    assert len(parsed) == 1
    assert parsed[0].test_case_id == "GEN001"
    assert parsed[0].expected_result == "The result is pass | fallback."
    assert "Legend" not in output
    assert output.count("|") == 37


def test_generate_from_chunks_reports_start_and_completion_for_each_segment():
    generator = Generator(llm_client=StubLLMClient())
    progress_events = []

    outputs = generator.generate_from_chunks(
        ["First requirement context", "Second requirement context"],
        progress=lambda index, total, state: progress_events.append(
            (index, total, state)
        ),
    )

    assert len(outputs) == 2
    assert progress_events == [
        (1, 2, "started"),
        (1, 2, "completed"),
        (2, 2, "started"),
        (2, 2, "completed"),
    ]


def test_generator_repairs_a_response_without_a_supported_table():
    repaired_table = """| Test Case ID | Module | Scenario | Pre Condition | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|---|
| TC001 | Account Services | Validate a record | None | 1. Submit the record. | The record is accepted. | P1 | Positive Case | Regression | UI Automation |
"""
    client = SequenceLLMClient([
        "I could not format a table, but the requirement describes validation.",
        repaired_table,
    ])
    generator = Generator(llm_client=client)

    output = generator.generate_from_chunk("BRD says to validate the record.")
    parsed = CaseParser().parse(output)

    assert len(client.prompts) == 2
    assert "DOCUMENT CONTENT" in client.prompts[1]
    assert "BRD says to validate the record." in client.prompts[1]
    assert len(parsed) == 1
    assert parsed[0].scenario == "Validate a record"


def test_generator_accepts_legacy_nine_column_table():
    legacy_table = """| Test Case ID | Module | Scenario | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|
| TC001 | Account Services | Validate a record | 1. Submit the record. | The record is accepted. | P1 | Positive Case | Regression | UI Automation |
"""
    generator = Generator(llm_client=SequenceLLMClient([legacy_table]))
    output = generator.generate_from_chunk("BRD says to validate the record.")
    parsed = CaseParser().parse(output)

    assert len(parsed) == 1
    assert parsed[0].pre_condition == "None"


def test_generator_normalizes_common_generic_category_labels():
    response = """| Test Case ID | Module | Scenario | Pre Condition | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type |
|---|---|---|---|---|---|---|---|---|---|
| TC001 | Account Services | Verify request handling at the API endpoint | None | 1. Send the request to the API endpoint. | The HTTP response is returned. | High | Functional | Performance | Automated |
| TC002 | Account Services | Verify behavior at the exact 90-day threshold | None | 1. Inspect the audit log. | The event is persisted for review. | Medium | Non‑Functional | Performance | Automated |
| TC003 | Account Services | Reject a request with missing information | None | 1. Click Submit without required information. | The request is rejected. | High | Functional | Regression | Automated |
"""
    generator = Generator(llm_client=SequenceLLMClient([response]))

    output = generator.generate_from_chunk("The BRD defines request rules.")
    parsed = CaseParser().parse(output)

    assert [case.priority for case in parsed] == ["P1", "P2", "P1"]
    assert [case.test_type for case in parsed] == [
        "Positive Case", "Edge Case", "Negative Case"
    ]
    assert [case.suite_type for case in parsed] == [
        "Regression", "Regression", "Regression"
    ]
    assert [case.automation_type for case in parsed] == [
        "API Automation", "Backend/DB", "UI Automation"
    ]


def test_generator_supplies_catalog_and_keeps_only_valid_requirement_references():
    response = """| Test Case ID | Module | Scenario | Pre Condition | Test Steps | Expected Result | Priority | Type | Suite Type | Automation Type | Requirement Reference |
|---|---|---|---|---|---|---|---|---|---|---|
| TC001 | Account Services | Validate a submitted record | None | 1. Submit it. | The record is validated. | P1 | Positive Case | Regression | UI Automation | REQ001, REQ999 |
"""
    client = SequenceLLMClient([response])
    generator = Generator(llm_client=client)

    output = generator.generate_from_chunk(
        "The system validates submitted records.",
        requirement_catalog=[{
            "requirement_id": "REQ001",
            "requirement": "The system validates submitted records.",
        }],
    )
    parsed = CaseParser().parse(output)

    assert "REQ001: The system validates submitted records." in client.prompts[0]
    assert parsed[0].requirement_reference == "REQ001"
    requirement = SimpleNamespace(
        requirement_id="REQ001",
        module="Account Services",
        requirement="The system validates submitted records.",
        status="ACTIVE",
    )
    assert build_requirement_test_case_mappings(
        [requirement], parsed
    ) == [("REQ001", "TC001")]
