"""Build conservative, domain-neutral requirement-to-test-case mappings."""

import re
from typing import Any, Iterable


STOP_WORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for",
    "in", "on", "with", "from", "that", "this", "is", "are",
    "be", "can", "must", "should", "shall", "system", "user",
    "state", "verify", "when", "ensure", "required",
    "requirement", "requirements",
    "via", "using", "based",
}

def _token_list(value: Any) -> list[str]:
    cleaned = "".join(
        character.casefold() if character.isalnum() else " "
        for character in str(value or "")
    )
    return [
        token
        for token in cleaned.split()
        if len(token) > 2 and token not in STOP_WORDS
    ]


def _tokens(value: Any) -> set[str]:
    return set(_token_list(value))


def _has_shared_specific_phrase(
    requirement_text: str,
    test_case_text: str,
    shared_tokens: set[str],
    distinctive_tokens: set[str],
) -> bool:
    """Require a shared adjacent phrase when only one distinctive term overlaps."""
    requirement_words = _token_list(requirement_text)
    test_case_words = _token_list(test_case_text)
    test_case_pairs = set(zip(test_case_words, test_case_words[1:]))
    return any(
        left in shared_tokens
        and right in shared_tokens
        and (left in distinctive_tokens or right in distinctive_tokens)
        and (left, right) in test_case_pairs
        for left, right in zip(requirement_words, requirement_words[1:])
    )


def build_requirement_test_case_mappings(
    requirements: Iterable[Any],
    test_cases: Iterable[Any],
    *,
    generated_test_cases: Iterable[Any] = (),
) -> list[tuple[str, str]]:
    """Return explicit or content-supported requirement/test-case pairs.

    Module names are used only to select a conservative overlap threshold;
    they are never counted as shared requirement content. Explicit
    ``requirement_reference`` values take precedence over lexical matching.
    """
    requirement_list = [
        requirement for requirement in (requirements or [])
        if getattr(requirement, "status", "ACTIVE") == "ACTIVE"
    ]
    active_cases_by_id = {
        str(getattr(case, "test_case_id", "")): case
        for case in test_cases
        if getattr(case, "status", "ACTIVE") == "ACTIVE"
    }
    # Use the current generation as the freshest source for explicit reference
    # metadata, but only for IDs already present in the active repository. This
    # lets a newly added traceability link be recorded even when a KEEP decision
    # correctly avoids creating a needless test-case content version.
    for candidate in generated_test_cases or []:
        test_case_id = str(getattr(candidate, "test_case_id", ""))
        if (
            test_case_id in active_cases_by_id
            and getattr(candidate, "status", "ACTIVE") == "ACTIVE"
        ):
            active_cases_by_id[test_case_id] = candidate
    active_cases = list(active_cases_by_id.values())

    # A term shared by many requirements or modules is weak evidence even
    # when it looks specific in isolation. Use the current requirement set
    # to identify distinctive terms without embedding a business vocabulary.
    requirement_terms: dict[str, set[str]] = {}
    term_owners: dict[str, set[str]] = {}
    for requirement in requirement_list:
        requirement_id = str(requirement.requirement_id)
        requirement_text = str(requirement.requirement or "")
        scope_tokens = _tokens(
            f"{getattr(requirement, 'module', '')} {requirement_text}"
        )
        requirement_terms[requirement_id] = _tokens(requirement_text)
        for token in scope_tokens:
            term_owners.setdefault(token, set()).add(requirement_id)

    mappings: list[tuple[str, str]] = []
    known_requirement_ids = set(requirement_terms)

    for requirement in requirement_list:
        requirement_id = str(requirement.requirement_id)
        requirement_text = str(requirement.requirement or "")
        requirement_tokens = requirement_terms[requirement_id]
        distinctive_tokens = {
            token for token in requirement_tokens
            if len(term_owners.get(token, set())) == 1
        }

        for test_case in active_cases:
            explicit_references = {
                reference.strip()
                for reference in re.split(
                    r"[,;]+",
                    str(getattr(test_case, "requirement_reference", "") or ""),
                )
                if reference.strip() in known_requirement_ids
            }
            if requirement_id in explicit_references:
                mappings.append(
                    (requirement_id, str(test_case.test_case_id))
                )
                continue

            test_case_tokens = _tokens(
                " ".join(
                    str(getattr(test_case, field, "") or "")
                    for field in (
                        "scenario",
                        "pre_condition",
                        "test_steps",
                        "expected_result",
                    )
                )
            )
            shared_content = requirement_tokens.intersection(test_case_tokens)
            shared_distinctive = shared_content.intersection(distinctive_tokens)
            supported = len(shared_distinctive) >= 3 or (
                len(shared_distinctive) == 1
                and _has_shared_specific_phrase(
                    requirement_text,
                    " ".join(
                        str(getattr(test_case, field, "") or "")
                        for field in (
                            "scenario",
                            "pre_condition",
                            "test_steps",
                            "expected_result",
                        )
                    ),
                    shared_content,
                    distinctive_tokens,
                )
            )

            if supported:
                mappings.append(
                    (requirement_id, str(test_case.test_case_id))
                )

    return mappings
