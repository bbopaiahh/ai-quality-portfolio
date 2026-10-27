# RARE — Requirement Analysis and Response Engine

**RARE** is a Streamlit-based AI test engineering assistant. It takes requirement documents, extracts candidate requirements, generates a structured master test suite, and compares the result with a local test case repository. It also connects test cases back to requirements so a reviewer can see coverage, gaps, and likely duplicate cases.

The project explores a practical QA question: can an AI-assisted workflow turn changing requirements into a test suite that is organized, traceable, and reviewable, while preserving the history of existing test cases?

## The end-to-end workflow

1. Upload one or more BRD or FSD documents in PDF or DOCX format.
2. RARE reads the document text and identifies candidate requirements using deterministic keyword and heading rules.
3. It compares those candidates with the saved requirement repository and reports KEEP, MODIFY, ADD, RETIRE, or REVIEW decisions.
4. The document is divided into overlapping sections and sent to the configured language model for test case generation.
5. Generated tables are parsed into structured cases; IDs are assigned and cases are compared with the existing test case repository.
6. RARE versions repository changes, creates requirement-to-test mappings, calculates coverage, and runs test-suite quality checks.
7. The dashboard shows the final suite and analysis, with an option to download the test cases as an Excel workbook.

**Flow:** PDF/DOCX → text extraction → candidate requirements → requirement synchronization → document chunking → AI test generation → parsing and ID resolution → test case change detection and versioning → traceability and coverage → quality analysis → dashboard and Excel export.

## What the generated test cases contain

The master suite is organized into these fields:

| Field | Purpose |
|---|---|
| Test Case ID | Stable identifier for a test case. |
| Module | Functional area associated with the case. |
| Scenario | Business-readable condition being tested. |
| Pre Condition | Required state before testing. |
| Test Steps | Actions used to exercise the scenario. |
| Expected Result | Observable behavior to verify. |
| Priority | Relative business importance. |
| Type | Positive, negative, end-to-end, or edge case. |
| Suite Type | Smoke, sanity, or regression classification. |
| Automation Type | UI, API, or backend/database automation classification. |

The generation prompt instructs the model to ground cases in the supplied requirement text, avoid inventing undocumented behavior, and return a structured Markdown table. The application parses that table into repository records. Generated content still needs review by a QA professional; model output and automated extraction can be incomplete or incorrect.

## Requirement handling and change history

Requirement extraction is rule-based in the current implementation. It looks for requirement-style wording and explicit module headings, then assigns candidate IDs, type, priority, and source-document information. This makes extraction predictable, but it is not a semantic guarantee: wording that does not match the rules can be missed, and a sentence that matches a keyword can be included when it is not a real requirement.

RARE compares newly extracted candidates with previously stored requirements and displays synchronization decisions. It preserves unchanged items, identifies additions and modifications, and surfaces uncertain cases for review. The current application does not authorize retirement based on an incomplete extraction or generation run, helping avoid treating a partial document read as proof that an old requirement was removed.

## Test repository, traceability, and quality checks

The test case repository stores structured cases and their status, version, source document, and timestamps. When a new suite is generated, RARE compares it with the existing records and summarizes KEEP, MODIFY, ADD, RETIRE, and REVIEW outcomes. Stable test case IDs allow the repository to show how cases change over time rather than presenting every generation as a brand-new list.

The dashboard also reports:

- **Requirement coverage:** covered and uncovered requirements, mapped and unmapped cases, and coverage percentage.
- **Traceability:** links between requirement records and test cases. Existing explicit references are used where available; the current automatic mapper also uses shared words and module names, so the links should be reviewed.
- **Suite quality:** an overall score, requirement gaps, duplicate or near-duplicate candidates, priority coverage, automation coverage, and test type distribution.
- **Change summary:** which repository records were kept, modified, added, retired, or flagged for review.
- **Excel export:** a formatted workbook of the current master suite for review and collaboration.

The codebase also contains a requirement-change impact analyzer that can identify test cases associated with changed requirements. This is a supporting service in the project; the main document-upload workflow centers on generation, repository synchronization, coverage, and quality analysis.

## Application structure

- **Streamlit interface:** accepts requirement documents and presents generation progress, repository changes, coverage, quality findings, and the final suite.
- **Document ingestion:** reads PDF and DOCX text, then breaks it into overlapping chunks so larger documents can be processed in segments.
- **Requirement extraction and repository:** creates structured requirement records and synchronizes them with saved JSON data.
- **LLM generation:** combines the project’s test-generation prompt with document chunks and parses the returned Markdown table.
- **Test case repository and versioning:** assigns case IDs, detects changes, and stores current records in JSON files.
- **Traceability and analysis:** maps requirements to cases, calculates coverage, identifies gaps and duplicate candidates, and summarizes suite quality.

## Technology

Python, Streamlit, PyPDF2, python-docx, OpenAI-compatible LLM clients, Groq, Gemini, Pydantic, Pandas, and OpenPyXL for Excel export. The application stores its requirement, test case, and traceability repositories as local JSON files.

## Current scope and review points

RARE is a proof of concept, not a validated autonomous test-authoring system. Its requirement extractor uses deterministic text rules, its automatic traceability includes word-overlap matching, and its test cases depend on language-model output. Those stages can miss context or suggest incorrect links, so reviewers should check the generated suite against the source document before relying on it.

The application currently accepts PDF and DOCX files. It uses configured external language-model services to process document chunks. Do not use confidential or personal requirement documents with the demo unless the chosen provider, data handling, and authorization have been reviewed. API keys belong in a local environment file and must not be published.

The source includes both Groq and Gemini provider settings. There is a provider-label mismatch in the current project: the UI says “Powered by Gemini,” while the LLM client tries Groq first and Gemini second when both are configured. Confirm the intended provider before presenting that UI label as accurate.

Repository data is local JSON, so it is useful for demonstrating a workflow but does not provide production-grade multi-user storage, access control, or audit governance. Human review remains necessary for extracted requirements, synchronization decisions, generated cases, and traceability links.

## Portfolio scope

This page describes the application and its Quality Engineering approach. The public portfolio shares documentation and selected, reviewed evidence. It does not publish the full working application source, local repository data, environment files, or API credentials.
