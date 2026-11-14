from __future__ import annotations

import json

from models.requirement import Requirement
from requirements.ambiguity_analyzer import RequirementAmbiguityAnalyzer


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.responses.pop(0)


def _requirement(requirement_id="REQ001", text="Apply a discount to eligible customers."):
    return Requirement(
        requirement_id=requirement_id,
        module="General",
        requirement=text,
        requirement_type="Business Rule",
        priority="P2",
    )


def _finding(evidence="Apply a discount to eligible customers.", requirement_id="REQ001"):
    return {
        "requirement_id": requirement_id,
        "category": "Undefined term",
        "description": "The eligibility criteria are not stated.",
        "evidence": evidence,
        "clarification_question": "What criteria make a customer eligible?",
        "confidence": 0.91,
    }


def test_returns_only_evidence_grounded_findings():
    source = "Apply a discount to eligible customers."
    llm = FakeLLM([json.dumps({"findings": [_finding()]})])

    result = RequirementAmbiguityAnalyzer(llm).analyze(
        [_requirement()], source
    )

    assert len(result) == 1
    assert result[0].evidence == source
    assert "do not assume an industry" in llm.prompts[0]


def test_discards_invented_source_quotes_and_unknown_requirement_ids():
    llm = FakeLLM([json.dumps({"findings": [
        _finding(evidence="Customers must have premium membership."),
        _finding(requirement_id="REQ999"),
    ]})])

    result = RequirementAmbiguityAnalyzer(llm).analyze(
        [_requirement()], "Apply a discount to eligible customers."
    )

    assert result == []


def test_rejects_quote_from_an_unrelated_part_of_the_document():
    requirement = _requirement(text="Process transaction.")
    unrelated_quote = "Eligible means current account holders only."
    source = (
        requirement.requirement
        + (" unrelated document text" * 20)
        + unrelated_quote
    )
    llm = FakeLLM([json.dumps({"findings": [
        _finding(evidence=unrelated_quote),
    ]})])

    result = RequirementAmbiguityAnalyzer(
        llm, context_chars=30
    ).analyze([requirement], source)

    assert result == []


def test_batches_large_input_without_losing_requirement_identity():
    requirements = [
        _requirement(f"REQ{i:03d}", f"The system shall process item {i}.")
        for i in range(1, 4)
    ]
    source = " ".join(item.requirement for item in requirements)
    llm = FakeLLM([
        json.dumps({"findings": []}),
        json.dumps({"findings": []}),
        json.dumps({"findings": []}),
    ])

    result = RequirementAmbiguityAnalyzer(
        llm, max_batch_chars=1, context_chars=20
    ).analyze(requirements, source)

    assert result == []
    assert len(llm.prompts) == 3


def test_empty_requirement_input_does_not_call_provider():
    llm = FakeLLM([])

    assert RequirementAmbiguityAnalyzer(llm).analyze([], "source") == []
    assert llm.prompts == []
