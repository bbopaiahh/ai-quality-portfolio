# The Judge — Multi-Tenant Configuration Drift Auditor

**The Judge** is a Quality Engineering proof of concept that checks whether a live web application matches the configuration expected for a tenant. It retrieves tenant-specific audit rules, inspects the rendered page with Playwright, compares expected and observed values, and presents the findings as PASS, WARNING, or FAIL results.

The problem it explores is familiar in multi-tenant software: one shared application can behave differently for different customers or environments. A configuration change or application release can leave the expected settings and the live interface out of sync. When there are many settings, manual comparison becomes slow and difficult to review.

## How the audit works

1. The Streamlit dashboard checks the configuration service and lets the user select a tenant.
2. The FastAPI service returns that tenant’s target URL and audit rules.
3. The audit engine opens the target form in a Playwright browser and inspects the configured elements.
4. For each rule, the engine compares the expected state with what it finds in the live DOM.
5. The dashboard summarizes the results and lets the user download a CSV report.

**Flow:** Streamlit dashboard → tenant selection → FastAPI configuration service → tenant audit rules → Python audit engine → Playwright browser → live application DOM → expected/actual comparison → dashboard findings and CSV report.

## What it checks

The current demonstration uses the public Practice Form Validation page at practice.expandtesting.com/form-validation. It inspects real DOM elements rather than relying on invented field names. Configurable checks in the proof of concept include:

- Whether a field exists in the page
- Whether an attribute such as required has the expected value
- Whether a field is visible
- Whether a field is enabled or disabled
- Whether an ID is duplicated across multiple elements

Three demo tenants are represented: Practice_Bank, Insurance_Demo, and Retail_Demo. The API-backed configuration is designed to give each tenant its own target and rules, while this proof of concept currently points them at the same public form. That keeps the demo focused on tenant-specific expectations and audit behavior, rather than on separate production applications.

## Understanding the results

| Status | Meaning | Demonstrated example |
|---|---|---|
| **PASS** | The observed state matches the configured expectation. | A required field is present and marked required. |
| **WARNING** | The rule can be evaluated, but the page has a structural issue worth reviewing. | Two elements share the same ID, making a locator ambiguous. |
| **FAIL** | The live state differs from the expected configuration, or the configured element is missing. | A field expected to be disabled is enabled, or an expected field is not found. |

Example rows from the included demo reports:

| Field / check | Expected | Observed | Result | What it shows |
|---|---:|---:|---|---|
| validationCustom01 — required | True | True | PASS | Expected attribute is present. |
| validationCustom05 — required | True | True | WARNING | Duplicate ID detected on the page. |
| validationCustom04 — disabled | True | False | FAIL | Configuration drift: the field is enabled. |
| validationCustom02 — configured attribute | True | Not found | FAIL | The expected element is absent from the live DOM. |

The sample reports are generated examples from the proof of concept. The CSV captures the tenant, timestamp, field ID, check type, property, expected value, actual value, status, and a short note. A structured report makes findings easier to review and gives a possible starting point for later reporting or pipeline integration.

## Dashboard and components

- **Streamlit dashboard:** Shows API health, tenant selection, the active configuration source, target application, number of configured rules, an audit action, status counts, row-level findings, and CSV download.
- **FastAPI configuration service:** Exposes a health check, tenant list, and tenant configuration endpoint. The current demo keeps API configurations in memory.
- **Python audit engine:** Retrieves rules, opens the target page, performs DOM checks, compares values, assigns statuses, and writes the report.
- **Playwright:** Reads the live page state, including element attributes, visibility, disabled state, existence, and duplicate IDs.
- **CSV reporting:** Preserves the result rows for review outside the dashboard.

The API configuration is the primary demonstration path. The ZIP also contains a local JSON fallback for Practice_Bank; it currently defines three rules, while the API configuration and sample reports demonstrate a broader set. Results can therefore vary depending on which configuration source is active. This is a known difference in the current proof of concept, not a claim that the two sources are synchronized.

## Quality Engineering focus

The value of this project is the verification approach: take an explicit expected configuration, observe the running interface independently, and produce evidence for both matches and mismatches. The demo deliberately includes positive matches, configuration drift, duplicate IDs, and missing-element cases so the audit output is useful to discuss in a QA review.

It also raises practical test-design questions:

- Is the configured element present in the rendered page?
- Does the live value match the tenant’s expected value?
- Could a duplicate selector make the check ambiguous?
- Can the result explain what was expected and what was observed?
- Can an auditor review the result without rerunning the browser session?

## Technology

Python, FastAPI, Uvicorn, Playwright, Streamlit, Pandas, Requests, and CSV reporting.

## Scope and limitations

The Judge is a **proof of concept**, not a production configuration-management or compliance platform. It uses a mock API with in-memory data, a public practice form, and local report files. The tenant examples share one target application. The project does not provide production authentication, tenant isolation, scheduled execution, historical audit storage, or deployment-grade security controls.

The architecture illustrates how a real configuration service could replace the mock API while keeping the core idea—compare expected settings with live application state. Any such production use would need appropriate authorization, tenant isolation, secret handling, network controls, and audit retention.

## Portfolio scope

This page explains the project’s purpose, workflow, implementation, and sample behavior. The public portfolio contains project documentation and selected evidence; it does not contain the full working application source or local environment files.
