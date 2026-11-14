from types import SimpleNamespace

from traceability.mapping_builder import (
    build_requirement_test_case_mappings,
)


def requirement(requirement_id, module, text):
    return SimpleNamespace(
        requirement_id=requirement_id,
        module=module,
        requirement=text,
    )


def test_explicit_requirement_reference_maps_even_without_shared_words():
    req = requirement("REQ001", "Records", "Validate the submitted record.")
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Archive",
        scenario="Submit an archive request",
        pre_condition="",
        test_steps="Open the archive screen.",
        expected_result="The request is saved.",
        requirement_reference="REQ001",
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings([req], [case]) == [
        ("REQ001", "TC001")
    ]


def test_multiple_explicit_requirement_references_map_without_lexical_overlap():
    reqs = [
        requirement("REQ001", "Records", "Validate a submitted record."),
        requirement("REQ002", "Archive", "Archive a completed request."),
    ]
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Cross-functional",
        scenario="Verify the combined workflow",
        pre_condition="",
        test_steps="Run the configured workflow.",
        expected_result="The workflow completes.",
        requirement_reference="REQ001, REQ002, UNKNOWN",
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings(reqs, [case]) == [
        ("REQ001", "TC001"),
        ("REQ002", "TC001"),
    ]


def test_generated_reference_can_add_mapping_for_kept_case_without_storing_a_new_version():
    req = requirement("REQ001", "Records", "Validate the submitted record.")
    stored = SimpleNamespace(
        test_case_id="TC001",
        module="Records",
        scenario="Validate a record",
        pre_condition="None",
        test_steps="Submit the record.",
        expected_result="The record is validated.",
        requirement_reference=None,
        status="ACTIVE",
    )
    generated = SimpleNamespace(
        test_case_id="TC001",
        module="Records",
        scenario="Validate a record",
        pre_condition="None",
        test_steps="Submit the record.",
        expected_result="The record is validated.",
        requirement_reference="REQ001",
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings(
        [req], [stored], generated_test_cases=[generated]
    ) == [("REQ001", "TC001")]


def test_shared_module_words_alone_do_not_create_a_mapping():
    req = requirement(
        "REQ001",
        "Customer Service",
        "The system must archive a customer request.",
    )
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Customer Service",
        scenario="Validate a customer profile",
        pre_condition="",
        test_steps="Open the profile and verify its name.",
        expected_result="The profile is displayed.",
        requirement_reference=None,
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings([req], [case]) == []


def test_content_overlap_maps_related_cases_but_not_other_requirements():
    reqs = [
        requirement(
            "REQ001",
            "General Service",
            "The system must validate the submitted record.",
        ),
        requirement(
            "REQ002",
            "General Service",
            "The system must accept an archive request and store confirmation.",
        ),
    ]
    cases = [
        SimpleNamespace(
            test_case_id="TC001",
            module="General Service",
            scenario="Validate a submitted record",
            pre_condition="A valid record is available",
            test_steps="Enter a valid record and submit it.",
            expected_result="The record is validated before saving.",
            requirement_reference=None,
            status="ACTIVE",
        ),
        SimpleNamespace(
            test_case_id="TC002",
            module="General Service",
            scenario="Verify an archive request is recorded",
            pre_condition="An archive request is ready for submission",
            test_steps="Open the archive screen and submit an archive request.",
            expected_result="The archive request confirmation is recorded successfully.",
            requirement_reference=None,
            status="ACTIVE",
        ),
    ]

    assert build_requirement_test_case_mappings(reqs, cases) == [
        ("REQ001", "TC001"),
        ("REQ002", "TC002"),
    ]


def test_one_generic_api_word_does_not_map_an_unrelated_requirement():
    req = requirement(
        "REQ001",
        "Credit Bureau",
        "The system must consume the CIBIL API via the documented specifications.",
    )
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Lead Search",
        scenario="Verify lead search results load within the required time",
        pre_condition="A large record set is available",
        test_steps="Execute a search query via the UI or API and measure duration.",
        expected_result="The results are returned within the time limit.",
        requirement_reference=None,
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings([req], [case]) == []


def test_two_distant_shared_terms_do_not_map_a_different_requirement_clause():
    req = requirement(
        "REQ001",
        "Lead Processing",
        "CIBIL score must exceed 650. Karza OCR must match the name on PAN.",
    )
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Document Checklist",
        scenario="Verify required documents for a salaried applicant",
        pre_condition="The lead is in document pending state",
        test_steps="Check PAN, identity records, and the Karza verification channel.",
        expected_result="The checklist matches the applicant category.",
        requirement_reference=None,
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings([req], [case]) == []


def test_common_module_and_single_generic_overlap_do_not_create_a_mapping():
    req = requirement(
        "REQ005",
        "Lead-to-Disbursement (L2D) Pipeline",
        "Performance: Lead search results must load in under 1.8 seconds for a database of 1M records.",
    )
    case = SimpleNamespace(
        test_case_id="TC045",
        module="Lead-to-Disbursement (L2D) Pipeline",
        scenario="Verify lead transitions to BM_Review when a PAN matches a record",
        pre_condition="An existing record is available",
        test_steps="Run the deduplication check against the matching record",
        expected_result="The lead moves to BM_Review",
        requirement_reference=None,
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings([req], [case]) == []


def test_distinctive_adjacent_phrase_can_support_a_mapping():
    req = requirement(
        "REQ001",
        "Credit Bureau",
        "The system must consume the CIBIL API through the documented request specifications.",
    )
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Integration",
        scenario="Verify a successful CIBIL API request",
        pre_condition="Valid credentials are available",
        test_steps="Send a request to the CIBIL API endpoint",
        expected_result="The API returns a response.",
        requirement_reference=None,
        status="ACTIVE",
    )

    assert build_requirement_test_case_mappings([req], [case]) == [
        ("REQ001", "TC001")
    ]


def test_inactive_test_cases_are_not_mapped():
    req = requirement("REQ001", "Nutrition", "Store the meal temperature.")
    case = SimpleNamespace(
        test_case_id="TC001",
        module="Nutrition",
        scenario="Store meal temperature",
        pre_condition="",
        test_steps="Measure and save the temperature.",
        expected_result="The meal temperature is stored.",
        requirement_reference="REQ001",
        status="RETIRED",
    )

    assert build_requirement_test_case_mappings([req], [case]) == []
