import io
import os
import re

import streamlit as st
import PyPDF2
from docx import Document

from config.settings import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    RARE_MAX_UPLOAD_BATCH_MB,
    RARE_MAX_UPLOAD_FILE_MB,
    RARE_MAX_UPLOAD_FILES,
    RARE_OCR_LANGUAGE,
    RARE_OCR_MIN_PAGE_CHARS,
    RARE_TESSERACT_CMD,
    SUPPORTED_DOCUMENT_TYPES,
)
from ingestion.upload_pipeline import (
    DocumentExtractionError,
    TesseractOCRBackend,
    UploadValidationError,
    extract_upload_batch,
)

from generation.test_generator import TestGenerator
from repository.test_case_change_detector import (
    ADD,
    KEEP,
    MODIFY,
    RETIRE,
    REVIEW,
    TestCaseChange,
    TestCaseChangeDetector,
)
from repository.test_case_retirement_policy import (
    eligible_test_case_ids_for_retired_requirements,
)
from repository.test_case_id_assigner import (
    TestCaseIdAssigner,
)
from repository.test_case_parser import (
    TestCaseParser,
)
from repository.test_case_repository import (
    TestCaseRepository,
)
from repository.test_case_service import (
    TestCaseService,
)
from repository.test_case_version_manager import (
    TestCaseVersionManager,
)
from repository.project_repository import ProjectRepository
from ui.project_workspace import render_project_workspace_selector
from requirements.requirement_extractor import RequirementExtractor
from requirements.ambiguity_analyzer import RequirementAmbiguityAnalyzer
from repository.requirement_repository import RequirementRepository
from repository.requirement_synchronization_service import (
    RequirementSynchronizationService,
)
from repository.traceability_repository import TraceabilityRepository
from traceability.traceability_service import TraceabilityService
from traceability.mapping_builder import (
    build_requirement_test_case_mappings,
)
from coverage.coverage_report import CoverageReport
from quality.test_suite_quality_analyzer import TestSuiteQualityAnalyzer
from quality.quality_report import QualityReport

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter


# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="RARE Framework",
    page_icon="🎯",
    layout="wide",
)


# ============================================================
# Application Components
# ============================================================

project_repository = ProjectRepository(
    registry_path=os.environ.get(
        "RARE_PROJECT_REGISTRY_PATH",
        "data/projects.json",
    ),
    workspace_root=os.environ.get("RARE_PROJECT_WORKSPACE_ROOT") or None,
)
active_project_id = render_project_workspace_selector(project_repository)

if active_project_id is None:
    repository_storage_paths = {
        "test_cases": "data/test_case_repository.json",
        "requirements": "data/requirement_repository.json",
        "traceability": "data/traceability_repository.json",
    }
else:
    repository_storage_paths = project_repository.get_repository_storage_paths(
        active_project_id
    )

test_generator = TestGenerator()

test_case_parser = TestCaseParser()

test_case_id_assigner = TestCaseIdAssigner()

test_case_repository = TestCaseRepository(
    storage_path=str(repository_storage_paths["test_cases"])
)

test_case_service = TestCaseService(
    repository=test_case_repository
)

change_detector = TestCaseChangeDetector()

version_manager = TestCaseVersionManager(
    repository=test_case_repository
)

requirement_extractor = RequirementExtractor()
requirement_repository = RequirementRepository(
    storage_path=str(repository_storage_paths["requirements"])
)
requirement_synchronization_service = RequirementSynchronizationService(
    repository=requirement_repository,
)

traceability_repository = TraceabilityRepository(
    storage_path=str(repository_storage_paths["traceability"])
)

traceability_service = TraceabilityService(
    requirement_repository=requirement_repository,
    test_case_repository=test_case_repository,
    traceability_repository=traceability_repository,
)

coverage_report = CoverageReport(
    traceability_service=traceability_service
)

quality_analyzer = TestSuiteQualityAnalyzer()


# ============================================================
# Helper Functions
# ============================================================

def get_next_test_case_number(
    existing_test_cases,
) -> int:
    """
    Determine the next available numeric Test Case ID.

    Example:

        TC001
        TC002
        TC007

    returns:

        8
    """

    highest_number = 0

    for test_case in existing_test_cases:

        test_case_id = (
            test_case.test_case_id
        )

        if not test_case_id.startswith("TC"):
            continue

        numeric_part = (
            test_case_id[2:]
        )

        if not numeric_part.isdigit():
            continue

        number = int(
            numeric_part
        )

        highest_number = max(
            highest_number,
            number,
        )

    return highest_number + 1


def display_change_summary(
    changes,
) -> None:
    """
    Display repository change detection results grouped in dropdowns.
    """

    summary = change_detector.summarize(changes)

    st.markdown("### Repository Change Summary")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("KEEP", summary[KEEP])
    col2.metric("MODIFY", summary[MODIFY])
    col3.metric("ADD", summary[ADD])
    col4.metric("RETIRE", summary[RETIRE])
    col5.metric("REVIEW", summary["REVIEW"])

    grouped = {
        KEEP: [],
        MODIFY: [],
        ADD: [],
        RETIRE: [],
        "REVIEW": [],
    }

    for change in changes:
        grouped.setdefault(change.action, []).append(change)

    for action, label in [
        (KEEP, "KEEP"),
        (MODIFY, "MODIFY"),
        (ADD, "ADD"),
        (RETIRE, "RETIRE"),
        ("REVIEW", "REVIEW"),
    ]:
        items = grouped.get(action, [])
        with st.expander(f"{label} ({len(items)})", expanded=False):
            if not items:
                st.caption("No test cases in this category.")
                continue

            for change in items:
                if action == ADD:
                    new_case = change.new_test_case
                    identifier = (
                        new_case.scenario
                        if new_case
                        else "New test case"
                    )
                else:
                    identifier = change.test_case_id or "New test case"

                st.write(
                    f"**{identifier}** — {change.reason}"
                )


# ============================================================
# Document Extraction
# ============================================================

def read_pdf(file) -> str:
    """
    Extract text from a PDF document.
    """

    text = ""

    try:

        reader = PyPDF2.PdfReader(file)

        for page in reader.pages:

            content = page.extract_text()

            if content:

                text += content + "\n"

    except Exception as exc:

        raise RuntimeError(
            f"Error reading PDF '{file.name}': {exc}"
        ) from exc

    return text


def read_docx(file) -> str:
    """
    Extract text from paragraphs and tables
    in a DOCX document.
    """

    text = []

    try:

        document = Document(file)

        # Paragraph content
        for paragraph in document.paragraphs:

            if paragraph.text.strip():

                text.append(
                    paragraph.text
                )

        # Table content
        for table in document.tables:

            for row in table.rows:

                for cell in row.cells:

                    if cell.text.strip():

                        text.append(
                            cell.text
                        )

    except Exception as exc:

        raise RuntimeError(
            f"Error reading DOCX '{file.name}': {exc}"
        ) from exc

    return "\n".join(text)


def extract_document_text(file) -> str:
    """
    Extract text based on the uploaded file type.
    """

    file_name = file.name.lower()

    if file_name.endswith(".pdf"):

        return read_pdf(file)

    if file_name.endswith(".docx"):

        return read_docx(file)

    raise ValueError(
        f"Unsupported file type: {file.name}"
    )


# ============================================================
# Chunking
# ============================================================

def create_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split document text using a sliding-window strategy.

    The overlap preserves contextual information between
    adjacent document chunks.
    """

    if not text or not text.strip():

        return []

    if overlap >= chunk_size:

        raise ValueError(
            "Chunk overlap must be smaller than "
            "chunk size."
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

            chunks.append(
                chunk
            )

    return chunks


# ============================================================
# Convert Test Cases to Display Markdown
# ============================================================

def _numbered_lines(value) -> str:
    """Convert <br>, HTML breaks, and existing lines into numbered lines."""

    text = str(value or "").replace("\r", "")
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    raw_lines = [line.strip() for line in text.split("\n") if line.strip()]

    cleaned = []
    for line in raw_lines:
        line = line.lstrip("-• \t")
        line = re.sub(r"^\d+[.)]\s*", "", line).strip()
        cleaned.append(line)

    return "\n".join(
        f"{index}. {line}"
        for index, line in enumerate(cleaned, start=1)
    )


def test_cases_to_markdown(test_cases) -> str:
    """Convert repository test cases to display Markdown."""

    headers = [
        "Test Case ID", "Module", "Scenario", "Pre Condition",
        "Test Steps", "Expected Result", "Priority", "Type",
        "Suite Type", "Automation Type",
    ]

    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for test_case in test_cases:
        values = [
            test_case.test_case_id,
            test_case.module,
            test_case.scenario,
            _numbered_lines(getattr(test_case, "pre_condition", "")),
            _numbered_lines(test_case.test_steps),
            _numbered_lines(test_case.expected_result),
            test_case.priority,
            test_case.test_type,
            test_case.suite_type,
            test_case.automation_type,
        ]

        values = [str(value).replace("|", "\\|").replace("\n", "<br>") for value in values]
        rows.append("| " + " | ".join(values) + " |")

    return "\n".join(rows)


def build_excel_workbook(test_cases) -> bytes:
    """Build a real Excel workbook for the Master Test Suite."""

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Master Test Suite"

    headers = [
        "Test Case ID", "Module", "Scenario", "Pre Condition",
        "Test Steps", "Expected Result", "Priority", "Type",
        "Suite Type", "Automation Type",
    ]

    worksheet.append(headers)

    for test_case in test_cases:
        worksheet.append([
            test_case.test_case_id,
            test_case.module,
            test_case.scenario,
            _numbered_lines(getattr(test_case, "pre_condition", "")),
            _numbered_lines(test_case.test_steps),
            _numbered_lines(test_case.expected_result),
            test_case.priority,
            test_case.test_type,
            test_case.suite_type,
            test_case.automation_type,
        ])

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    widths = [16, 22, 42, 42, 55, 55, 12, 18, 18, 22]
    for index, width in enumerate(widths, start=1):
        worksheet.column_dimensions[get_column_letter(index)].width = width

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


# ============================================================
# UI Header
# ============================================================

st.title(
    "RARE: Requirement Analysis and Response Engine"
)

st.markdown(
    "### Enterprise AI-Driven Test Design and Requirement Mapping"
)

st.markdown(
    "#### Powered by Gemini"
)

st.divider()


# ============================================================
# Upload Section
# ============================================================

uploaded_files = st.file_uploader(
    "Upload Requirement Documents (FSD/BRD)",
    type=SUPPORTED_DOCUMENT_TYPES,
    accept_multiple_files=True,
    max_upload_size=RARE_MAX_UPLOAD_FILE_MB,
    help=(
        f"Upload up to {RARE_MAX_UPLOAD_FILES} PDF, Word, or image files. "
        f"Each file can be up to {RARE_MAX_UPLOAD_FILE_MB} MB; the full batch "
        f"can be up to {RARE_MAX_UPLOAD_BATCH_MB} MB. Scanned pages and images "
        "are read with the configured local OCR engine."
    ),
)

include_ambiguity_review = st.checkbox(
    "Include AI requirement ambiguity review (additional provider call)",
    value=False,
    help=(
        "Uses the configured AI provider to flag unclear requirement wording "
        "with quotations checked against the uploaded documents."
    ),
)


# ============================================================
# Generation
# ============================================================

if st.button(
    "Generate Master Test Suite",
    type="primary",
):

    for previous_proposal in st.session_state.get(
        "rare_pending_retirements", []
    ):
        st.session_state.pop(
            f"rare_retire_{previous_proposal.test_case_id}",
            None,
        )
    st.session_state.pop("rare_pending_retirements", None)

    all_document_text = []
    source_documents = []
    extracted_documents = []

    with st.status(
        "Architecting Test Suite...",
        expanded=True,
    ) as status:

        # ----------------------------------------------------
        # 1. Document Extraction
        # ----------------------------------------------------

        st.write(
            "### 1. Document Extraction"
        )

        try:
            extracted_documents = extract_upload_batch(
                uploaded_files,
                max_files=RARE_MAX_UPLOAD_FILES,
                max_file_bytes=RARE_MAX_UPLOAD_FILE_MB * 1024 * 1024,
                max_batch_bytes=RARE_MAX_UPLOAD_BATCH_MB * 1024 * 1024,
                ocr_backend=TesseractOCRBackend(
                    tesseract_cmd=RARE_TESSERACT_CMD
                ),
                ocr_language=RARE_OCR_LANGUAGE,
                min_native_page_chars=RARE_OCR_MIN_PAGE_CHARS,
                progress=st.write,
            )
        except (DocumentExtractionError, UploadValidationError) as exc:
            st.error(str(exc))
            st.stop()

        all_document_text = [
            document.as_context_text()
            for document in extracted_documents
        ]
        source_documents = [
            document.file_name
            for document in extracted_documents
        ]
        for document in extracted_documents:
            st.caption(
                f"{document.file_name}: {len(document.text):,} characters "
                f"using {document.extraction_method}; "
                f"OCR pages: {document.ocr_page_count}."
            )

        if not all_document_text:

            st.error(
                "No readable text was found in "
                "the uploaded documents."
            )

            st.stop()

        combined_text = "\n\n".join(
            all_document_text
        )

        source_document = ", ".join(
            source_documents
        )

        # ----------------------------------------------------
        # 2. Requirement Extraction + Repository Integration
        # ----------------------------------------------------

        st.write(
            "### 2. Requirement Extraction + Repository"
        )

        status.update(
            label=(
                "Analyzing requirements with the configured AI provider..."
            ),
            state="running",
        )
        st.caption(
            "Requirement extraction is in progress. The provider call is "
            "synchronous, so its response may take a little time."
        )

        try:

            extracted_requirements = requirement_extractor.extract(
                combined_text,
                source_document=source_document,
            )

        except Exception as exc:

            st.error(
                "Requirement extraction failed."
            )

            st.exception(exc)

            st.stop()

        status.update(
            label=(
                "Requirement extraction complete; synchronizing results..."
            ),
            state="running",
        )

        if not extracted_requirements:

            st.warning(
                "No structured requirements were extracted "
                "from the uploaded documents. The existing requirement "
                "repository was left unchanged."
            )

        else:

            if include_ambiguity_review:
                st.write("#### Requirement ambiguity review")
                st.caption(
                    "The AI checks for unclear or missing decision details using only "
                    "the uploaded text. Findings are advisory and do not change stored requirements."
                )
                status.update(
                    label="Reviewing requirement clarity with the configured AI provider...",
                    state="running",
                )
                try:
                    ambiguity_findings = RequirementAmbiguityAnalyzer(
                        test_generator.llm_client
                    ).analyze(extracted_requirements, combined_text)
                    if ambiguity_findings:
                        st.warning(
                            f"AI flagged {len(ambiguity_findings)} possible clarification "
                            "need(s). Review these against the source before confirming behavior."
                        )
                        with st.expander(
                            f"Ambiguity findings ({len(ambiguity_findings)})",
                            expanded=True,
                        ):
                            for finding in ambiguity_findings:
                                st.markdown(
                                    f"**{finding.requirement_id} · {finding.category}** "
                                    f"(confidence {finding.confidence:.0%})"
                                )
                                st.write(finding.description)
                                st.caption(f"Source evidence: “{finding.evidence}”")
                                st.info(f"Clarification: {finding.clarification_question}")
                    else:
                        st.success(
                            "No evidence-backed ambiguity findings were returned for "
                            "the extracted requirements."
                        )
                except Exception as exc:
                    st.warning(
                        "Ambiguity review could not be completed. Requirement and test "
                        "processing will continue; no ambiguity findings were applied."
                    )
                    st.caption(str(exc))

            try:

                # The extraction may be incomplete, so retirement is deliberately
                # not authorized by this application workflow.
                synchronization_report = (
                    requirement_synchronization_service.synchronize(
                        extracted_requirements,
                        generation_complete=False,
                        retirement_candidates=set(),
                    )
                )

                action_counts = synchronization_report.counts
                st.success(
                    "Requirement synchronization completed: "
                    f"**{action_counts['KEEP']} KEEP**, "
                    f"**{action_counts['MODIFY']} MODIFY**, "
                    f"**{action_counts['ADD']} ADD**, "
                    f"**{action_counts['RETIRE']} RETIRE**, and "
                    f"**{action_counts['REVIEW']} REVIEW**."
                )

                latest_requirements = requirement_repository.get_all()
                st.write(
                    f"Requirement repository now contains "
                    f"**{len(latest_requirements)}** latest requirement records."
                )

                with st.expander(
                    f"Requirement synchronization details "
                    f"({len(synchronization_report.proposed_changes)} decisions)",
                    expanded=False,
                ):
                    for action in ("KEEP", "MODIFY", "ADD", "RETIRE", "REVIEW"):
                        action_changes = [
                            change for change in synchronization_report.proposed_changes
                            if change.action == action
                        ]
                        st.markdown(f"**{action} ({len(action_changes)})**")
                        if not action_changes:
                            st.caption("No requirements in this category.")
                            continue

                        for change in action_changes:
                            candidate = (
                                change.new_requirement
                                or change.existing_requirement
                            )
                            requirement_text = (
                                candidate.requirement
                                if candidate is not None
                                else change.requirement_id or "Requirement"
                            )
                            stable_id = (
                                change.requirement_id
                                or (
                                    change.existing_requirement.requirement_id
                                    if change.existing_requirement is not None
                                    else "Pending ID assignment"
                                )
                            )
                            st.write(
                                f"- **{stable_id}** — {requirement_text} "
                                f"\n  - {change.reason}"
                            )

                if synchronization_report.review_required:
                    st.warning(
                        f"{len(synchronization_report.review_required)} requirement "
                        "decision(s) need manual review. They were not applied."
                    )

            except Exception as exc:

                st.error(
                    "Requirement synchronization failed."
                )

                st.exception(exc)

                st.stop()

        # ----------------------------------------------------
        # 3. Chunking
        # ----------------------------------------------------

        st.write(
            "### 3. Document Chunking"
        )

        chunks = []
        for extracted_document in extracted_documents:
            chunks.extend(
                create_chunks(
                    extracted_document.as_context_text(),
                )
            )

        if not chunks:

            st.error(
                "Document chunking produced no content."
            )

            st.stop()

        st.write(
            f"Created **{len(chunks)}** "
            "contextual document segments."
        )

        # ----------------------------------------------------
        # 4. AI Test Generation
        # ----------------------------------------------------

        st.write(
            "### 4. AI Test Generation"
        )

        status.update(
            label=(
                f"Generating test cases from {len(chunks)} document segments..."
            ),
            state="running",
        )
        generation_progress = st.progress(
            0,
            text=(
                f"Waiting to start AI generation across {len(chunks)} segments."
            ),
        )

        def update_generation_progress(
            segment_index: int,
            segment_total: int,
            event: str,
        ) -> None:
            completed_segments = segment_index - 1
            completed_percent = int(
                completed_segments * 100 / max(segment_total, 1)
            )

            if event == "started":
                generation_progress.progress(
                    completed_percent,
                    text=(
                        f"Waiting for the AI provider response for segment "
                        f"{segment_index} of {segment_total}. "
                        f"{completed_segments} of {segment_total} segments complete."
                    ),
                )
                status.update(
                    label=(
                        f"AI is generating test cases for segment "
                        f"{segment_index} of {segment_total}..."
                    ),
                    state="running",
                )
            elif event == "completed":
                completed_segments = segment_index
                completed_percent = int(
                    completed_segments * 100 / max(segment_total, 1)
                )
                generation_progress.progress(
                    completed_percent,
                    text=(
                        f"Completed {completed_segments} of "
                        f"{segment_total} segments."
                    ),
                )
                status.update(
                    label=(
                        f"AI generation completed for segment "
                        f"{segment_index} of {segment_total}."
                    ),
                    state="running",
                )
            elif event == "failed":
                generation_progress.progress(
                    completed_percent,
                    text=(
                        f"Generation stopped on segment {segment_index} "
                        f"of {segment_total}; see the error below."
                    ),
                )
                status.update(
                    label=(
                        f"AI generation failed on segment "
                        f"{segment_index} of {segment_total}."
                    ),
                    state="error",
                )

        try:

            generated_results = (
                test_generator.generate_from_chunks(
                    chunks,
                    requirement_catalog=[
                        requirement
                        for requirement in requirement_repository.get_all()
                        if getattr(requirement, "status", "ACTIVE") == "ACTIVE"
                    ],
                    progress=update_generation_progress,
                )
            )

        except Exception as exc:

            st.error(
                "Test generation failed."
            )

            st.exception(exc)

            st.stop()

        status.update(
            label=(
                f"AI generation complete for {len(generated_results)} of "
                f"{len(chunks)} segments; parsing results..."
            ),
            state="running",
        )

        if not generated_results:

            st.error(
                "The AI did not generate any "
                "test cases."
            )

            st.stop()

        generation_segment_count = len(generated_results)
        generation_complete = generation_segment_count == len(chunks)

        st.write(
            f"Generated validated output from "
            f"**{generation_segment_count}** of **{len(chunks)}** segments."
        )

        # ----------------------------------------------------
        # 5. Parse Generated Test Cases
        # ----------------------------------------------------

        st.write(
            "### 5. Test Case Parsing"
        )

        parsed_chunks = []

        try:

            for generated_result in generated_results:

                parsed_cases = (
                    test_case_parser.parse(
                        generated_result,
                        source_document=source_document,
                    )
                )

                if parsed_cases:

                    parsed_chunks.append(
                        parsed_cases
                    )

        except Exception as exc:

            st.error(
                "Test case parsing failed."
            )

            st.exception(exc)

            st.stop()

        if not parsed_chunks:

            st.error(
                "No test cases could be parsed "
                "from the generated output."
            )

            st.stop()

        parsed_segment_count = len(parsed_chunks)
        generation_complete = generation_complete and (
            parsed_segment_count == generation_segment_count
        )

        if not generation_complete:
            st.warning(
                "Generation was incomplete or one or more generated segments "
                "could not be parsed. Unmatched existing test cases will be "
                "marked REVIEW and will not be retired."
            )

        parsed_count = sum(
            len(chunk)
            for chunk in parsed_chunks
        )

        st.write(
            f"Parsed **{parsed_count}** "
            "test cases."
        )

        # ----------------------------------------------------
        # 6. Existing Repository
        # ----------------------------------------------------

        st.write(
            "### 6. Existing Repository"
        )

        try:

            existing_test_cases = (
                test_case_service.get_all_test_cases()
            )

        except Exception as exc:

            st.error(
                "Failed to load the existing "
                "test case repository."
            )

            st.exception(exc)

            st.stop()

        st.write(
            f"Loaded **{len(existing_test_cases)}** "
            "existing test cases."
        )

        # ----------------------------------------------------
        # 7. Test Case Identity Resolution
        # ----------------------------------------------------

        st.write(
            "### 7. Test Case Identity Resolution"
        )

        try:

            next_number = (
                get_next_test_case_number(
                    existing_test_cases
                )
            )

            globally_assigned_cases = (
                test_case_id_assigner.assign_from_chunks(
                    parsed_chunks,
                    start_number=next_number,
                )
            )

        except Exception as exc:

            st.error(
                "Test case identity assignment failed."
            )

            st.exception(exc)

            st.stop()

        if not globally_assigned_cases:

            st.error(
                "Test case identity assignment "
                "produced no test cases."
            )

            st.stop()

        st.write(
            f"Prepared **{len(globally_assigned_cases)}** "
            "generated test cases for repository comparison."
        )

        # ----------------------------------------------------
        # 8. Change Detection
        # ----------------------------------------------------

        st.write(
            "### 8. Repository Change Detection"
        )

        try:

            retirement_candidates = eligible_test_case_ids_for_retired_requirements(
                requirement_repository.get_all(),
                traceability_repository.get_all(),
                existing_test_cases,
            )

            changes = change_detector.detect(
                existing_test_cases=existing_test_cases,
                new_test_cases=globally_assigned_cases,
                generation_complete=generation_complete,
                retirement_candidates=retirement_candidates,
            )

        except Exception as exc:

            st.error(
                "Repository change detection failed."
            )

            st.exception(exc)

            st.stop()

        retirement_proposals = [
            change for change in changes
            if change.action == RETIRE
        ]
        if retirement_proposals:
            st.session_state["rare_pending_retirements"] = retirement_proposals
            changes = [
                TestCaseChange(
                    action=REVIEW,
                    test_case_id=change.test_case_id,
                    existing_test_case=change.existing_test_case,
                    reason=(
                        "Retirement proposed; awaiting explicit user confirmation. "
                        + change.reason
                    ),
                ) if change.action == RETIRE else change
                for change in changes
            ]

        change_summary = (
            change_detector.summarize(
                changes
            )
        )

        st.write(
            "Detected: "
            f"**{change_summary[KEEP]} KEEP**, "
            f"**{change_summary[MODIFY]} MODIFY**, "
            f"**{change_summary[ADD]} ADD**, "
            f"**{change_summary[RETIRE]} RETIRE**, "
            f"**{change_summary['REVIEW']} REVIEW**."
        )

        # ----------------------------------------------------
        # 9. Version Management
        # ----------------------------------------------------

        st.write(
            "### 9. Version Management"
        )

        try:

            affected_cases = (
                version_manager.apply_changes(
                    changes
                )
            )

        except Exception as exc:

            st.error(
                "Repository version management failed."
            )

            st.exception(exc)

            st.stop()

        st.write(
            f"Applied repository changes to "
            f"**{len(affected_cases)}** test cases."
        )

        # ----------------------------------------------------
        # 10. Traceability
        # ----------------------------------------------------

        st.write(
            "### 10. Traceability"
        )

        try:

            current_requirements = requirement_repository.get_all()
            final_repository_cases = test_case_service.get_all_test_cases()

            traceability_pairs = build_requirement_test_case_mappings(
                current_requirements,
                final_repository_cases,
                generated_test_cases=globally_assigned_cases,
            )

            created_mappings = 0
            existing_mapping_pairs = {
                (mapping.requirement_id, mapping.test_case_id)
                for mapping in traceability_repository.get_all()
            }

            for requirement_id, test_case_id in traceability_pairs:
                if (requirement_id, test_case_id) in existing_mapping_pairs:
                    continue

                traceability_service.create_mapping(
                    requirement_id=requirement_id,
                    test_case_id=test_case_id,
                )
                created_mappings += 1

            total_mappings = traceability_repository.count()

            st.write(
                f"Created **{created_mappings}** new requirement-to-test-case "
                f"mappings. Traceability repository contains **{total_mappings}** mappings."
            )

        except Exception as exc:

            st.error(
                "Traceability integration failed."
            )

            st.exception(exc)

            st.stop()

        # ----------------------------------------------------
        # 11. Coverage Analysis
        # ----------------------------------------------------

        st.write(
            "### 11. Coverage Analysis"
        )

        try:

            coverage_summary = (
                coverage_report.generate_summary()
            )

            covered_requirements = (
                coverage_report.get_covered_requirements()
            )

            uncovered_requirements = (
                coverage_report.get_uncovered_requirements()
            )

            unmapped_test_cases = (
                coverage_report.get_unmapped_test_cases()
            )

            coverage_details = (
                coverage_report.get_requirement_coverage_details()
            )

        except Exception as exc:

            st.error(
                "Coverage analysis failed."
            )

            st.exception(exc)

            st.stop()

        coverage_col1, coverage_col2 = st.columns(2)
        coverage_col3, coverage_col4 = st.columns(2)

        coverage_col1.metric(
            "Total Requirements",
            coverage_summary["total_requirements"],
        )

        coverage_col2.metric(
            "Covered Requirements",
            coverage_summary["covered_requirements"],
        )

        coverage_col3.metric(
            "Uncovered Requirements",
            coverage_summary["uncovered_requirements"],
        )

        coverage_col4.metric(
            "Coverage Percentage",
            f'{coverage_summary["coverage_percentage"]:.2f}%',
        )

        st.markdown(
            "#### Covered Requirements"
        )

        if covered_requirements:

            for requirement in covered_requirements:

                requirement_mapping = next(
                    (
                        detail
                        for detail in coverage_details
                        if detail["requirement_id"]
                        == requirement.requirement_id
                    ),
                    None,
                )

                mapped_test_cases = (
                    requirement_mapping["test_case_ids"]
                    if requirement_mapping
                    else []
                )

                st.success(
                    f"**{requirement.requirement_id}** — "
                    f"{requirement.module} — "
                    f"{requirement.requirement}"
                )

                if mapped_test_cases:

                    st.caption(
                        "Mapped Test Cases: "
                        + ", ".join(mapped_test_cases)
                    )

        else:

            st.info(
                "No covered requirements found."
            )

        st.markdown(
            "#### Uncovered Requirements"
        )

        if uncovered_requirements:

            for requirement in uncovered_requirements:

                st.warning(
                    f"**{requirement.requirement_id}** — "
                    f"{requirement.module} — "
                    f"{requirement.requirement}"
                )

        else:

            st.success(
                "All active requirements are covered."
            )

        st.markdown(
            "#### Unmapped Test Cases"
        )

        if unmapped_test_cases:

            for test_case in unmapped_test_cases:

                st.info(
                    f"**{test_case.test_case_id}** — "
                    f"{test_case.module} — "
                    f"{test_case.scenario}"
                )

        else:

            st.success(
                "All active test cases are mapped to at least one requirement."
            )

        # ----------------------------------------------------
        # 12. Test Suite Quality & Gap Analysis
        # ----------------------------------------------------

        st.write(
            "### 12. Test Suite Quality & Gap Analysis"
        )

        try:
            quality_requirements = requirement_repository.get_all()
            quality_test_cases = test_case_service.get_all_test_cases()
            quality_mappings = traceability_repository.get_all()

            quality_report = quality_analyzer.analyze(
                requirements=quality_requirements,
                test_cases=quality_test_cases,
                mappings=quality_mappings,
            )

        except Exception as exc:
            st.error(
                "Test suite quality analysis failed."
            )
            st.exception(exc)
            st.stop()

        quality_report = QualityReport(quality_report).generate_report()

        quality_summary = quality_report["summary"]

        quality_col1, quality_col2, quality_col3 = st.columns(3)

        quality_col1.metric(
            "Quality Score",
            f'{quality_summary["quality_score"]:.1f}/100',
        )

        quality_col2.metric(
            "Duplicate Candidates",
            quality_summary["duplicate_candidates"],
        )

        quality_col3.metric(
            "Requirements With Gaps",
            quality_summary["requirements_with_gaps"],
        )

        quality_col4, quality_col5 = st.columns(2)

        quality_col4.metric(
            "Single-Test Requirements",
            quality_summary["single_test_requirements"],
        )

        quality_col5.metric(
            "Active Test Cases",
            quality_summary["total_test_cases"],
        )

        st.markdown(
            "#### Requirement Coverage Gaps"
        )

        requirement_gaps = quality_report["requirement_gaps"]

        if requirement_gaps:
            for gap in requirement_gaps:
                st.warning(
                    f'**{gap["requirement_id"]}** — '
                    f'{gap["module"]} — '
                    f'{gap["requirement"]}'
                )

                st.caption(
                    "Mapped Test Cases: "
                    + (
                        ", ".join(gap["mapped_test_cases"])
                        if gap["mapped_test_cases"]
                        else "None"
                    )
                )

                st.caption(
                    "Gaps: "
                    + "; ".join(gap["gap_reasons"])
                )
        else:
            st.success(
                "No requirement coverage gaps detected."
            )

        st.markdown(
            "#### Duplicate / Near-Duplicate Test Cases"
        )

        duplicate_candidates = quality_report["duplicates"]

        if duplicate_candidates:
            for duplicate in duplicate_candidates:
                st.warning(
                    f'**{duplicate.first_test_case_id}** ↔ '
                    f'**{duplicate.second_test_case_id}** — '
                    f'{duplicate.similarity:.2%} similarity — '
                    f'{duplicate.reason}'
                )
        else:
            st.success(
                "No duplicate or near-duplicate test cases detected."
            )

        st.markdown(
            "#### Priority Coverage"
        )

        priority_analysis = quality_report["priority_analysis"]

        for priority in ("P0", "P1", "P2"):
            priority_data = priority_analysis[priority]

            if priority_data["total"] == 0:
                continue

            st.write(
                f'**{priority} Requirements:** '
                f'{priority_data["covered_by_p0_p1"]}/'
                f'{priority_data["total"]} covered by P0/P1 test cases.'
            )

            if priority_data["gaps"]:
                st.caption(
                    "Priority gaps: "
                    + ", ".join(priority_data["gaps"])
                )

        st.markdown(
            "#### Automation Coverage"
        )

        automation_analysis = quality_report["automation_analysis"]

        automation_col1, automation_col2 = st.columns(2)

        automation_col1.metric(
            "Automated Test Cases",
            automation_analysis["automated_test_cases"],
        )

        automation_col2.metric(
            "Automation Percentage",
            f'{automation_analysis["automation_percentage"]:.2f}%',
        )

        st.write(
            "Automation by Type:"
        )

        for automation_type, count in automation_analysis["by_type"].items():
            st.write(
                f"- **{automation_type}**: {count}"
            )

        if automation_analysis["manual_or_unknown_ids"]:
            st.caption(
                "Manual/Unknown Test Cases: "
                + ", ".join(
                    automation_analysis["manual_or_unknown_ids"]
                )
            )

        st.markdown(
            "#### Test Type Distribution"
        )

        test_type_analysis = quality_report["test_type_analysis"]

        for test_type, count in test_type_analysis["counts"].items():
            percentage = test_type_analysis["percentages"][test_type]

            st.write(
                f"- **{test_type}**: "
                f'{count} ({percentage:.2f}%)'
            )

        # ----------------------------------------------------
        # 13. Final Repository State
        # ----------------------------------------------------

        st.write(
            "### 13. Final Repository State"
        )

        try:

            final_repository_cases = (
                test_case_service.get_all_test_cases()
            )

        except Exception as exc:

            st.error(
                "Failed to read the final repository state."
            )

            st.exception(exc)

            st.stop()

        st.write(
            f"Repository now contains "
            f"**{len(final_repository_cases)}** "
            "current test cases."
        )

        status.update(
            label=(
                "Master Test Suite generated, "
                "compared, versioned, and stored successfully."
            ),
            state="complete",
        )

    display_change_summary(changes)

    # --------------------------------------------------------
    # Change Summary
    # --------------------------------------------------------

pending_retirements = st.session_state.get(
    "rare_pending_retirements", []
)
retirement_notice = st.session_state.pop("rare_retirement_notice", None)
if retirement_notice:
    st.success(retirement_notice)

if pending_retirements:
    st.warning(
        f"{len(pending_retirements)} existing test case(s) appear obsolete. "
        "Review the proposed archive actions. They remain active until you confirm."
    )
    with st.form("rare_retirement_review_form"):
        for proposal in pending_retirements:
            existing_case = proposal.existing_test_case
            case_id = proposal.test_case_id
            summary = (
                existing_case.scenario
                if existing_case is not None
                else "Existing test case"
            )
            st.checkbox(
                f"Archive {case_id}: {summary} — {proposal.reason}",
                key=f"rare_retire_{case_id}",
                value=False,
            )
        confirm_retirements = st.form_submit_button(
            "Confirm retirement of selected cases",
            type="primary",
        )
        keep_in_review = st.form_submit_button(
            "Keep all proposed cases active for now"
        )

    if confirm_retirements:
        selected_retirement_ids = {
            proposal.test_case_id
            for proposal in pending_retirements
            if st.session_state.get(f"rare_retire_{proposal.test_case_id}", False)
        }
        if not selected_retirement_ids:
            st.warning("Select at least one proposed case to archive.")
        else:
            selected_proposals = [
                proposal for proposal in pending_retirements
                if proposal.test_case_id in selected_retirement_ids
            ]
            try:
                cases_to_retire = [
                    proposal for proposal in selected_proposals
                    if (
                        test_case_service.get_test_case(proposal.test_case_id)
                        is not None
                        and test_case_service.get_test_case(proposal.test_case_id).status
                        != "RETIRED"
                    )
                ]
                retired_cases = version_manager.apply_changes(cases_to_retire)
                for case_id in selected_retirement_ids:
                    for mapping in traceability_repository.get_by_test_case(
                        case_id
                    ):
                        if mapping.status == "ACTIVE":
                            traceability_service.deactivate_mapping(
                                mapping.requirement_id,
                                mapping.test_case_id,
                            )
            except Exception as exc:
                st.error(
                    "The archive action or its traceability update failed. "
                    "Check the repository before retrying."
                )
                st.exception(exc)
            else:
                st.session_state.pop("rare_pending_retirements", None)
                for case_id in selected_retirement_ids:
                    st.session_state.pop(f"rare_retire_{case_id}", None)
                st.session_state["rare_retirement_notice"] = (
                    f"Archived {len(selected_retirement_ids)} test case(s). "
                    "Their IDs and version history were preserved."
                )
                st.rerun()

    if keep_in_review:
        st.session_state.pop("rare_pending_retirements", None)
        for proposal in pending_retirements:
            st.session_state.pop(f"rare_retire_{proposal.test_case_id}", None)
        st.session_state["rare_retirement_notice"] = (
            "No test cases were archived. Proposed cases remain active for later review."
        )
        st.rerun()

# ============================================================
# Repository Display
# ============================================================

repository_test_cases = (
    test_case_service.get_all_test_cases()
)


if repository_test_cases:

    st.success(
        f"Master Test Suite available — "
        f"{len(repository_test_cases)} test cases."
    )

    st.divider()

    st.markdown(
        "### Final Master Test Suite"
    )

    display_columns = {
        "Test Case ID": [tc.test_case_id for tc in repository_test_cases],
        "Module": [tc.module for tc in repository_test_cases],
        "Scenario": [tc.scenario for tc in repository_test_cases],
        "Pre Condition": [_numbered_lines(getattr(tc, "pre_condition", "")) for tc in repository_test_cases],
        "Test Steps": [_numbered_lines(tc.test_steps) for tc in repository_test_cases],
        "Expected Result": [_numbered_lines(tc.expected_result) for tc in repository_test_cases],
        "Priority": [tc.priority for tc in repository_test_cases],
        "Type": [tc.test_type for tc in repository_test_cases],
        "Suite Type": [tc.suite_type for tc in repository_test_cases],
        "Automation Type": [tc.automation_type for tc in repository_test_cases],
    }

    st.dataframe(
        display_columns,
        width="stretch",
        hide_index=True,
    )

    excel_data = build_excel_workbook(repository_test_cases)

    st.download_button(
        label="Download Master Test Suite (Excel)",
        data=excel_data,
        file_name="Master_Test_Suite.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()

    st.markdown(
        "### Repository Summary"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Test Cases",
        len(repository_test_cases),
    )

    col2.metric(
        "Active Test Cases",
        sum(
            1
            for test_case in repository_test_cases
            if test_case.status == "ACTIVE"
        ),
    )

    col3.metric(
        "Repository Records",
        test_case_service.count_records(),
    )

else:

    st.info(
        "No test cases are currently stored "
        "in the repository."
    )
