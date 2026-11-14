from types import SimpleNamespace

from repository.test_case_retirement_policy import (
    eligible_test_case_ids_for_retired_requirements,
)


def test_absent_cases_are_not_archive_candidates_without_retired_requirements():
    requirements = [SimpleNamespace(requirement_id="REQ001", status="ACTIVE")]
    cases = [SimpleNamespace(test_case_id="TC001", status="ACTIVE")]

    assert eligible_test_case_ids_for_retired_requirements(
        requirements, [], cases
    ) == set()


def test_only_active_cases_linked_to_retired_requirements_are_candidates():
    requirements = [
        SimpleNamespace(requirement_id="REQ001", status="RETIRED"),
        SimpleNamespace(requirement_id="REQ002", status="ACTIVE"),
    ]
    mappings = [
        SimpleNamespace(
            requirement_id="REQ001",
            test_case_id="TC001",
            status="ACTIVE",
        ),
        SimpleNamespace(
            requirement_id="REQ002",
            test_case_id="TC002",
            status="ACTIVE",
        ),
        SimpleNamespace(
            requirement_id="REQ001",
            test_case_id="TC003",
            status="REVIEW",
        ),
    ]
    cases = [
        SimpleNamespace(test_case_id="TC001", status="ACTIVE"),
        SimpleNamespace(test_case_id="TC002", status="ACTIVE"),
        SimpleNamespace(test_case_id="TC003", status="ACTIVE"),
        SimpleNamespace(test_case_id="TC004", status="RETIRED"),
    ]

    assert eligible_test_case_ids_for_retired_requirements(
        requirements, mappings, cases
    ) == {"TC001"}


def test_stored_reference_can_link_case_to_retired_requirement():
    requirements = [SimpleNamespace(requirement_id="REQ001", status="RETIRED")]
    case = SimpleNamespace(
        test_case_id="TC001",
        status="ACTIVE",
        requirement_reference="REQ001, REQ002",
    )

    assert eligible_test_case_ids_for_retired_requirements(
        requirements, [], [case]
    ) == {"TC001"}
