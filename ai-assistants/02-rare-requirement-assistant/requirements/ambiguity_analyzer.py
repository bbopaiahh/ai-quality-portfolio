"""Evidence-checked, domain-neutral requirement ambiguity analysis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

from models.requirement import Requirement


@dataclass(frozen=True)
class AmbiguityFinding:
    """A proposed clarification need linked to an exact source quotation."""

    requirement_id: str
    category: str
    description: str
    evidence: str
    clarification_question: str
    confidence: float


class RequirementAmbiguityAnalyzer:
    """Use the configured LLM to find unclear requirements without domain rules.

    Findings are advisory, are never persisted here, and are accepted only when
    the cited evidence appears verbatim (apart from whitespace) in the source.
    """

    def __init__(
        self,
        llm_client,
        *,
        max_batch_chars: int = 12_000,
        context_chars: int = 1_200,
    ):
        if max_batch_chars < 1 or context_chars < 1:
            raise ValueError("Analysis text limits must be positive.")
        self.llm_client = llm_client
        self.max_batch_chars = max_batch_chars
        self.context_chars = context_chars

    def analyze(
        self,
        requirements: Iterable[Requirement],
        source_text: str,
    ) -> list[AmbiguityFinding]:
        requirements = list(requirements or [])
        if not requirements or not source_text.strip():
            return []

        source_index = _WhitespaceIndex(source_text)
        batches: list[list[tuple[Requirement, str]]] = []
        current: list[tuple[Requirement, str]] = []
        current_size = 0

        for requirement in requirements:
            context = self._context_for(requirement, source_text, source_index)
            entry_size = len(requirement.requirement) + len(context) + 120
            if current and current_size + entry_size > self.max_batch_chars:
                batches.append(current)
                current = []
                current_size = 0
            current.append((requirement, context))
            current_size += entry_size
        if current:
            batches.append(current)

        findings: list[AmbiguityFinding] = []
        known_ids = {item.requirement_id for item in requirements}
        for batch in batches:
            findings.extend(
                self._analyze_batch(batch, known_ids)
            )
        return findings

    def _context_for(
        self,
        requirement: Requirement,
        source_text: str,
        source_index: "_WhitespaceIndex",
    ) -> str:
        location = source_index.find(requirement.requirement)
        if location is None:
            return requirement.requirement[: self.context_chars]
        start, end = location
        half_context = self.context_chars // 2
        return source_text[max(0, start - half_context): min(
            len(source_text), max(end, start + half_context)
        )]

    def _analyze_batch(
        self,
        batch: list[tuple[Requirement, str]],
        known_ids: set[str],
    ) -> list[AmbiguityFinding]:
        requirement_payload = [
            {
                "requirement_id": requirement.requirement_id,
                "requirement": requirement.requirement,
                "source_context": context,
            }
            for requirement, context in batch
        ]
        prompt = (
            "Review these requirements for ambiguity, missing decision criteria, "
            "undefined terms, unclear boundaries, conflicting wording, or unstated "
            "assumptions. Use only the supplied text; do not assume an industry, "
            "regulation, product behavior, or acceptance rule. Return only a JSON "
            "object shaped as {\"findings\":[{\"requirement_id\":string,"
            "\"category\":string,\"description\":string,\"evidence\":string,"
            "\"clarification_question\":string,\"confidence\":number}]}. "
            "Each finding must cite an exact quotation from its source_context. "
            "Do not create findings when the text is sufficiently precise.\n\n"
            + json.dumps(requirement_payload, ensure_ascii=False)
        )
        raw = self.llm_client.generate(prompt, temperature=0, max_tokens=3000)
        payload = _parse_json_object(raw)
        raw_findings = payload.get("findings", [])
        if not isinstance(raw_findings, list):
            raise ValueError("Ambiguity response 'findings' must be a list.")

        evidence_context_by_id = {
            requirement.requirement_id: context
            for requirement, context in batch
        }
        accepted: list[AmbiguityFinding] = []
        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            requirement_id = _clean_text(item.get("requirement_id"))
            category = _clean_text(item.get("category"))
            description = _clean_text(item.get("description"))
            evidence = _clean_text(item.get("evidence"))
            question = _clean_text(item.get("clarification_question"))
            if (
                requirement_id not in known_ids
                or not all((category, description, evidence, question))
                or not _contains_quote(
                    evidence_context_by_id.get(requirement_id, ""), evidence
                )
            ):
                continue
            try:
                confidence = float(item.get("confidence", 0))
            except (TypeError, ValueError):
                continue
            if not 0 <= confidence <= 1:
                continue
            accepted.append(AmbiguityFinding(
                requirement_id=requirement_id,
                category=category,
                description=description,
                evidence=evidence,
                clarification_question=question,
                confidence=confidence,
            ))
        return accepted


class _WhitespaceIndex:
    """Locate a requirement while tolerating line-wrap and spacing changes."""

    def __init__(self, text: str):
        self.text = text

    def find(self, value: str) -> tuple[int, int] | None:
        parts = value.split()
        if not parts:
            return None
        pattern = r"\s+".join(re.escape(part) for part in parts)
        match = re.search(pattern, self.text, flags=re.IGNORECASE)
        return match.span() if match else None


def _parse_json_object(response: str) -> dict:
    text = (response or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Ambiguity response did not contain a JSON object.")
        payload = json.loads(text[start:end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Ambiguity response must be a JSON object.")
    return payload


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _contains_quote(source_text: str, quote: str) -> bool:
    normalized_source = re.sub(r"\s+", " ", source_text).casefold()
    normalized_quote = re.sub(r"\s+", " ", quote).casefold().strip()
    return bool(normalized_quote and normalized_quote in normalized_source)
