import os
import subprocess
import sys
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="The Judge | Configuration Drift Auditor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# APPLICATION CONSTANTS
# =========================================================

APP_DIR = os.path.dirname(os.path.abspath(__file__))

API_BASE_URL = "http://127.0.0.1:8000"
TENANTS_ENDPOINT = f"{API_BASE_URL}/api/tenants"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

REPORT_DIRECTORY = os.path.join(APP_DIR, "audit_reports")


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    /* =====================================================
       GLOBAL
    ===================================================== */

    .stApp {
        background: #0b0f14;
        color: #f5f7fa;
    }

    [data-testid="stAppViewContainer"] {
        background: #0b0f14;
    }

    [data-testid="stHeader"] {
        background: #0b0f14;
    }

    [data-testid="stMain"] .block-container {
        max-width: 1500px;
        padding-top: 2.2rem;
        padding-bottom: 2rem;
    }

    /* =====================================================
       SIDEBAR
    ===================================================== */

    section[data-testid="stSidebar"] {
        background: #141820;
        border-right: 1px solid #29303a;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.8rem;
    }

    .sidebar-brand {
        font-size: 21px;
        font-weight: 750;
        color: #f5f7fa;
        margin-bottom: 2px;
    }

    .sidebar-subtitle {
        color: #8f9aaa;
        font-size: 12px;
        margin-bottom: 22px;
    }

    .sidebar-section {
        color: #dfe5ec;
        font-size: 13px;
        font-weight: 650;
        margin-top: 12px;
        margin-bottom: 10px;
    }

    .api-status {
        border-radius: 8px;
        padding: 11px 12px;
        font-size: 12px;
        font-weight: 600;
        margin: 8px 0 18px 0;
    }

    .api-online {
        background: #123b29;
        border: 1px solid #1c6a45;
        color: #55d98c;
    }

    .api-offline {
        background: #421d20;
        border: 1px solid #7a2f35;
        color: #ff7b83;
    }

    .source-box {
        background: #10141b;
        border: 1px solid #252c36;
        border-radius: 8px;
        padding: 10px 11px;
        color: #8fc7ff;
        font-family: Consolas, monospace;
        font-size: 11px;
        overflow-wrap: anywhere;
        margin-bottom: 18px;
    }

    /* =====================================================
       HEADER
    ===================================================== */

    .hero {
        padding: 4px 0 2px 0;
    }

    .hero-row {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .hero-icon {
        font-size: 39px;
        line-height: 1;
    }

    .hero-title {
        font-size: 38px;
        line-height: 1;
        font-weight: 760;
        letter-spacing: -0.7px;
        color: #f7f9fb;
    }

    .hero-subtitle {
        color: #7fabc9;
        font-size: 13px;
        margin-top: 9px;
        margin-bottom: 13px;
    }

    .hero-description {
        color: #c3cbd5;
        font-size: 14px;
        line-height: 1.6;
        max-width: 1050px;
        margin-bottom: 8px;
    }

    /* =====================================================
       SECTION HEADINGS
    ===================================================== */

    .section-title {
        color: #f5f7fa;
        font-size: 18px;
        font-weight: 700;
        margin: 4px 0 12px 0;
    }

    .section-caption {
        color: #7f8997;
        font-size: 12px;
        margin-top: -5px;
        margin-bottom: 14px;
    }

    .section-divider {
        height: 1px;
        background: #29303a;
        margin: 24px 0;
    }

    /* =====================================================
       TENANT INFO CARDS
    ===================================================== */

    .info-card {
        background: #141920;
        border: 1px solid #2a313b;
        border-radius: 10px;
        padding: 15px 17px;
        min-height: 82px;
    }

    .info-label {
        color: #788595;
        font-size: 10px;
        font-weight: 650;
        letter-spacing: 0.6px;
        margin-bottom: 9px;
    }

    .info-value {
        color: #eef2f6;
        font-size: 15px;
        font-weight: 600;
        overflow-wrap: anywhere;
    }

    .info-value-url {
        color: #8fc7ff;
        font-size: 12px;
        font-family: Consolas, monospace;
        overflow-wrap: anywhere;
    }

    /* =====================================================
       KPI CARDS
    ===================================================== */

    .kpi-card {
        background: #141920;
        border: 1px solid #2a313b;
        border-radius: 10px;
        padding: 16px 18px;
        min-height: 94px;
    }

    .kpi-label {
        color: #7e8a99;
        font-size: 10px;
        font-weight: 650;
        letter-spacing: 0.7px;
        margin-bottom: 8px;
    }

    .kpi-value {
        color: #f5f7fa;
        font-size: 29px;
        font-weight: 760;
        line-height: 1;
    }

    .kpi-total {
        border-left: 3px solid #48b9ff;
    }

    .kpi-pass {
        border-left: 3px solid #2ecc71;
    }

    .kpi-warning {
        border-left: 3px solid #f1c40f;
    }

    .kpi-fail {
        border-left: 3px solid #ff5b62;
    }

    /* =====================================================
       AUDIT STATUS BANNER
    ===================================================== */

    .audit-ready {
        background: #132d43;
        border: 1px solid #1e5278;
        color: #82c7ff;
        border-radius: 8px;
        padding: 11px 14px;
        font-size: 13px;
    }

    /* =====================================================
       REPORT AREA
    ===================================================== */

    .report-card {
        background: #141920;
        border: 1px solid #2a313b;
        border-radius: 10px;
        padding: 15px 17px;
    }

    .report-name {
        color: #e7edf3;
        font-family: Consolas, monospace;
        font-size: 12px;
    }

    .report-meta {
        color: #758190;
        font-size: 11px;
        margin-top: 5px;
    }

    /* =====================================================
       FOOTER
    ===================================================== */

    .footer {
        color: #626e7c;
        font-size: 11px;
        text-align: center;
        padding: 28px 0 8px 0;
        line-height: 1.7;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_api_health():
    """Check whether the mock production configuration API is running."""
    try:
        response = requests.get(
            HEALTH_ENDPOINT,
            timeout=5,
        )

        if response.status_code == 200:
            return True, response.json()

        return False, None

    except requests.RequestException:
        return False, None


def get_tenants():
    """Retrieve available tenants from the configuration API."""
    try:
        response = requests.get(
            TENANTS_ENDPOINT,
            timeout=5,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("tenants", [])

    except requests.RequestException as error:
        st.error(
            f"Unable to retrieve tenants from the configuration API: {error}"
        )
        return []


def get_tenant_config(tenant):
    """Retrieve configuration for the selected tenant."""
    try:
        url = f"{API_BASE_URL}/api/tenants/{tenant}/config"

        response = requests.get(
            url,
            timeout=5,
        )
        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        st.error(
            f"Unable to retrieve configuration for {tenant}: {error}"
        )
        return None


def run_judge(tenant):
    """Execute Judge Engine for the selected tenant."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(APP_DIR, "judge_engine.py"),
                tenant,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=APP_DIR,
        )

        if result.returncode != 0:
            return False, result.stdout, result.stderr

        return True, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return (
            False,
            "",
            "The audit exceeded the 120-second execution limit.",
        )

    except Exception as error:
        return (
            False,
            "",
            str(error),
        )


def get_report_path(tenant):
    """Return the generated CSV report path."""
    filename = f"drift_report_{tenant}.csv"
    return os.path.join(
        REPORT_DIRECTORY,
        filename,
    )


def load_report(tenant):
    """Load the generated CSV report."""
    report_path = get_report_path(tenant)

    if not os.path.exists(report_path):
        return None

    try:
        return pd.read_csv(report_path)

    except Exception as error:
        st.error(
            f"Unable to read audit report: {error}"
        )
        return None


def display_status_table(df):
    """Display audit results with clean professional formatting."""

    display_df = df.copy()

    column_mapping = {
        "Field_ID": "Field ID",
        "Check_Type": "Check Type",
        "Check": "Check Type",
        "Rule": "Rule",
        "Expected": "Expected",
        "Actual": "Actual",
        "Status": "Status",
        "Notes": "Notes",
        "Timestamp": "Timestamp",
    }

    display_df = display_df.rename(
        columns=column_mapping
    )

    for column in ["Expected", "Actual"]:
        if column in display_df.columns:
            display_df[column] = display_df[column].apply(
                lambda value: str(value)
                if pd.notna(value)
                else ""
            )

    preferred_columns = [
        "Field ID",
        "Check Type",
        "Rule",
        "Expected",
        "Actual",
        "Status",
        "Notes",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in display_df.columns
    ]

    display_df = display_df[available_columns]

    def style_status(value):
        if value == "PASS":
            return "color: #2ecc71; font-weight: 700"

        if value == "WARNING":
            return "color: #f1c40f; font-weight: 700"

        if value == "FAIL":
            return "color: #ff5b62; font-weight: 700"

        return ""

    if "Status" in display_df.columns:
        styled_df = display_df.style.map(
            style_status,
            subset=["Status"],
        )
    else:
        styled_df = display_df

    st.dataframe(
        styled_df,
        width="stretch",
        hide_index=True,
        height=390,
    )


# =========================================================
# SESSION STATE
# =========================================================

if "last_audited_tenant" not in st.session_state:
    st.session_state["last_audited_tenant"] = None

if "last_audit_time" not in st.session_state:
    st.session_state["last_audit_time"] = None

if "last_audit_output" not in st.session_state:
    st.session_state["last_audit_output"] = ""


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-brand">⚖️ The Judge</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-subtitle">Configuration Drift Auditor</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-section">Audit Configuration</div>',
        unsafe_allow_html=True,
    )

    api_healthy, health_data = get_api_health()

    if api_healthy:
        st.markdown(
            """
            <div class="api-status api-online">
                🟢 Configuration API Online
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="api-status api-offline">
                🔴 Configuration API Offline
            </div>
            """,
            unsafe_allow_html=True,
        )

    tenants = get_tenants()

    if tenants:
        selected_tenant = st.selectbox(
            "Select Tenant",
            tenants,
            index=0,
        )
    else:
        selected_tenant = None
        st.warning("No tenants available.")

    st.markdown(
        '<div class="sidebar-section">Configuration Source</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="source-box">{API_BASE_URL}</div>',
        unsafe_allow_html=True,
    )

    run_button = st.button(
        "▶  Run Audit",
        width="stretch",
        type="primary",
    )

    st.markdown("---")

    st.caption(
        "The Judge executes the audit engine locally and retrieves "
        "tenant configuration from the mock production API."
    )


# =========================================================
# MAIN HEADER
# =========================================================

st.markdown(
    """
    <div class="hero">
      <div class="hero-row">
        <div class="hero-icon">⚖️</div>
        <div class="hero-title">The Judge</div>
      </div>
      <div class="hero-subtitle">Multi-Tenant Configuration Drift Auditor</div>
      <div class="hero-description">The Judge retrieves tenant-specific configuration from the production configuration source, validates the live application DOM, and identifies configuration drift.</div>
    </div>
    """.replace("\n    ", "\n"),
    unsafe_allow_html=True,
)


# =========================================================
# NO TENANT
# =========================================================

if not selected_tenant:
    st.warning(
        "Select a tenant from the sidebar to begin."
    )
    st.stop()


# =========================================================
# LOAD TENANT CONFIGURATION
# =========================================================

config = get_tenant_config(
    selected_tenant
)

if not config:
    st.error(
        "Unable to load tenant configuration."
    )
    st.stop()


audit_rules = config.get(
    "audit_rules",
    [],
)

target_url = config.get(
    "target_url",
    "N/A",
)


# =========================================================
# TENANT INFORMATION
# =========================================================

st.markdown(
    '<div class="section-divider"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="section-title">Tenant: {selected_tenant}</div>',
    unsafe_allow_html=True,
)

info_col1, info_col2 = st.columns(
    2,
    gap="medium",
)

with info_col1:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-label">CONFIGURED AUDIT RULES</div>
            <div class="info-value">{len(audit_rules)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with info_col2:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-label">TARGET APPLICATION</div>
            <div class="info-value-url">{target_url}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# RUN AUDIT
# =========================================================

if run_button:

    st.markdown(
        '<div class="section-divider"></div>',
        unsafe_allow_html=True,
    )

    progress_placeholder = st.empty()

    progress_placeholder.markdown(
        f"""
        <div class="audit-ready">
            Running The Judge for <strong>{selected_tenant}</strong>...
        </div>
        """,
        unsafe_allow_html=True,
    )

    success, stdout, stderr = run_judge(
        selected_tenant
    )

    if success:

        progress_placeholder.success(
            f"Audit completed successfully for {selected_tenant}."
        )

        st.session_state["last_audited_tenant"] = selected_tenant
        st.session_state["last_audit_time"] = datetime.now().strftime(
            "%d %b %Y, %H:%M:%S"
        )
        st.session_state["last_audit_output"] = stdout

    else:

        progress_placeholder.error(
            f"Audit failed for {selected_tenant}."
        )

        if stderr:
            with st.expander("View execution details"):
                st.code(stderr)

        st.stop()


# =========================================================
# DETERMINE WHICH REPORT TO DISPLAY
# =========================================================

report_tenant = st.session_state.get(
    "last_audited_tenant"
)

if report_tenant != selected_tenant:

    st.markdown(
        '<div class="section-divider"></div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Select a tenant and click **Run Audit** to begin."
    )

    st.stop()


# =========================================================
# LOAD AUDIT REPORT
# =========================================================

report_df = load_report(
    selected_tenant
)

if report_df is None:

    st.warning(
        "Audit completed, but the CSV report could not be found."
    )

    st.stop()


# =========================================================
# AUDIT SUMMARY
# =========================================================

total_rules = len(report_df)

pass_count = int(
    (report_df["Status"] == "PASS").sum()
)

warning_count = int(
    (report_df["Status"] == "WARNING").sum()
)

fail_count = int(
    (report_df["Status"] == "FAIL").sum()
)


# =========================================================
# AUDIT RESULTS HEADER
# =========================================================

st.markdown(
    '<div class="section-divider"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Audit Results</div>',
    unsafe_allow_html=True,
)

last_audit_time = st.session_state.get(
    "last_audit_time"
)

if last_audit_time:
    st.markdown(
        f'<div class="section-caption">'
        f'Last audit: {last_audit_time}'
        f'</div>',
        unsafe_allow_html=True,
    )


# =========================================================
# KPI CARDS
# =========================================================

col1, col2, col3, col4 = st.columns(
    4,
    gap="medium",
)

with col1:
    st.markdown(
        f"""
        <div class="kpi-card kpi-total">
            <div class="kpi-label">TOTAL RULES</div>
            <div class="kpi-value">{total_rules}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="kpi-card kpi-pass">
            <div class="kpi-label">PASS</div>
            <div class="kpi-value">{pass_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="kpi-card kpi-warning">
            <div class="kpi-label">WARNING</div>
            <div class="kpi-value">{warning_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="kpi-card kpi-fail">
            <div class="kpi-label">FAIL</div>
            <div class="kpi-value">{fail_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# AUDIT RESULT TABLE
# =========================================================

st.markdown(
    '<div class="section-divider"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Detailed Audit Results</div>',
    unsafe_allow_html=True,
)

display_status_table(
    report_df
)


# =========================================================
# REPORT DOWNLOAD
# =========================================================

st.markdown(
    '<div class="section-divider"></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Audit Report</div>',
    unsafe_allow_html=True,
)

report_path = get_report_path(
    selected_tenant
)

if os.path.exists(report_path):

    report_filename = os.path.basename(
        report_path
    )

    with open(
        report_path,
        "rb",
    ) as report_file:

        report_bytes = report_file.read()

    report_col1, report_col2 = st.columns(
        [1, 4],
        gap="medium",
    )

    with report_col1:
        st.download_button(
            label="⬇ Download CSV Report",
            data=report_bytes,
            file_name=report_filename,
            mime="text/csv",
            width="stretch",
        )

    with report_col2:
        st.markdown(
            f"""
            <div class="report-card">
                <div class="report-name">{report_filename}</div>
                <div class="report-meta">
                    Generated by The Judge · {selected_tenant}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        <strong>The Judge</strong> · Multi-Tenant Configuration Drift Auditor
        <br>
        FastAPI · Playwright · Pandas · Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
