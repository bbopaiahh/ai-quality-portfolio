"""Safe archive eligibility derived from explicitly retired requirements."""

from __future__ import annotations

import re
from typing import Iterable


def eligible_test_case_ids_for_retired_requirements(
    requirements: Iterable[object],
    mappings: Iterable[object],
    test_cases: Iterable[object],
) -> set[str]:
    """Return active case IDs linked to requirements already marked RETIRED.

    Absence from the latest generated suite is not sufficient evidence to archive
    a case. A case must be linked to an explicitly retired requirement through an
    active traceability record or its stored requirement-reference field.
    """
    retired_ids = {
        str(_field(requirement, "requirement_id", ""))
        for requirement in requirements or []
        if str(_field(requirement, "status", "ACTIVE")).upper() == "RETIRED"
    }
    if not retired_ids:
        return set()

    active_case_ids = {
        str(_field(case, "test_case_id", ""))
        for case in test_cases or []
        if str(_field(case, "status", "ACTIVE")).upper() == "ACTIVE"
    }
    candidates = {
        str(_field(mapping, "test_case_id", ""))
        for mapping in mappings or []
        if str(_field(mapping, "status", "ACTIVE")).upper() == "ACTIVE"
        and str(_field(mapping, "requirement_id", "")) in retired_ids
    }
    for case in test_cases or []:
        if str(_field(case, "status", "ACTIVE")).upper() != "ACTIVE":
            continue
        references = {
            part.strip()
            for part in re.split(
                r"[,;]+",
                str(_field(case, "requirement_reference", "") or ""),
            )
            if part.strip()
        }
        if references.intersection(retired_ids):
            candidates.add(str(_field(case, "test_case_id", "")))
    return candidates.intersection(active_case_ids)


def _field(value: object, name: str, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)
