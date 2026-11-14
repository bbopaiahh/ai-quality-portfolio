# The Judge --- Multi-Tenant Configuration Drift Auditor

**The Judge** is a Proof of Concept (POC) for a **multi-tenant
configuration drift auditing system**.

It retrieves tenant-specific configuration rules from a mock production
configuration API, opens the tenant's live application, inspects the DOM
using Playwright, compares the live application state against the
expected configuration, and produces a structured audit result with:

-   PASS
-   WARNING
-   FAIL

The project also provides a **Streamlit dashboard** so the complete
audit can be demonstrated through a browser instead of only from the
command line.

------------------------------------------------------------------------

## 1. Project Overview

Modern SaaS applications often serve multiple tenants or customers from
a common application platform.

Although the underlying application may be shared, each tenant can have
different configuration requirements, such as:

-   Whether a field is mandatory
-   Whether a field is visible
-   Whether a field is enabled or disabled
-   Whether a configured attribute has a particular value
-   Whether an expected field exists in the live application
-   Whether the DOM structure contains unexpected issues such as
    duplicate IDs

Over time, configuration can drift from what was originally intended.

For example:

``` text
Production Configuration
        |
        | Expected
        v
+-----------------------+
| Contact field required|
| Payment enabled       |
| Payment visible       |
+-----------------------+

        VS

Live Application DOM
        |
        | Actual
        v
+-----------------------+
| Contact required      | PASS
| Payment enabled       | PASS
| Payment visible       | PASS
+-----------------------+
```

If the application changes without the configuration source being
updated, or if the configuration changes without the application being
updated, the two can become inconsistent.

**The Judge** is designed to detect this kind of configuration drift.

------------------------------------------------------------------------

# 2. What The Judge Does

The current POC follows this flow:

``` text
                  +-------------------------+
                  |   Streamlit Dashboard   |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  |     Select Tenant       |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  | Mock Production Config  |
                  |        FastAPI          |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  |   Tenant Audit Rules    |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  |     Judge Engine        |
                  |      Playwright         |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  |    Live Application     |
                  |         DOM             |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  | Compare Expected vs     |
                  |        Actual           |
                  +------------+------------+
                               |
                 +-------------+-------------+
                 |             |             |
                 v             v             v
               PASS         WARNING        FAIL
                 |             |             |
                 +-------------+-------------+
                               |
                               v
                  +-------------------------+
                  | CSV Audit Report        |
                  +-------------------------+
```

------------------------------------------------------------------------

# 3. Key Features

## Multi-Tenant Support

The mock configuration API currently contains multiple tenants:

-   `Practice_Bank`
-   `Insurance_Demo`
-   `Retail_Demo`

Each tenant has its own:

-   Target application URL
-   Audit rules
-   Expected configuration
-   Intentional drift scenarios

This demonstrates that the same audit engine can operate against
different tenant configurations.

------------------------------------------------------------------------

## Production Configuration API

A FastAPI service acts as the mock production configuration source.

Example endpoint:

``` text
GET /api/tenants/{tenant}/config
```

Example:

``` text
http://127.0.0.1:8000/api/tenants/Practice_Bank/config
```

The API returns the tenant's configuration and audit rules.

There is also a health endpoint:

``` text
GET /health
```

And a tenant listing endpoint:

``` text
GET /api/tenants
```

------------------------------------------------------------------------

## Live DOM Inspection

The Judge uses **Playwright** to open the configured target application
and inspect the live DOM.

The current POC uses:

``` text
https://practice.expandtesting.com/form-validation
```

The inspection process can evaluate:

-   Element ID
-   Element name
-   Element type
-   Required attribute
-   Disabled state
-   Visibility
-   Attribute values
-   Element existence
-   Duplicate IDs

------------------------------------------------------------------------

# 4. Current DOM Inspection Example

The target form currently exposes fields such as:

``` text
validationCustom01
validationCustom05
validationCustom04
```

The inspection script is:

``` text
inspect_form.py
```

It is useful during development because it shows what the live page
actually contains.

Example command:

``` powershell
python inspect_form.py
```

The inspector reports information such as:

``` text
Tag
ID
Name
Type
Required
Max Length
Min Length
Disabled
Visible
Value
```

This helped create the initial real-field audit matrix instead of
inventing arbitrary field names.

------------------------------------------------------------------------

# 5. Audit Engine

The main audit engine is:

``` text
judge_engine.py
```

It accepts the tenant name as a command-line argument.

Example:

``` powershell
python judge_engine.py Practice_Bank
```

Another example:

``` powershell
python judge_engine.py Insurance_Demo
```

And:

``` powershell
python judge_engine.py Retail_Demo
```

The engine:

1.  Receives the tenant name.
2.  Calls the mock production configuration API.
3.  Retrieves tenant-specific rules.
4.  Opens the configured target application.
5.  Locates the configured DOM element.
6.  Performs the requested check.
7.  Compares expected and actual values.
8.  Generates PASS/WARNING/FAIL.
9.  Saves the audit result as a CSV report.

------------------------------------------------------------------------

# 6. Audit Statuses

The Judge currently uses three statuses.

## PASS

The live application matches the expected configuration.

Example:

``` text
Expected: True
Actual:   True
Status:   PASS
```

Typical note:

``` text
Matched
```

------------------------------------------------------------------------

## WARNING

A structural issue is detected, but the requested configuration check
itself may still match.

The current POC demonstrates duplicate IDs.

Example:

``` text
Field ID: validationCustom05

2 elements share this ID.
```

The result is reported as:

``` text
WARNING
```

This is useful because duplicate IDs can create ambiguity for automation
and configuration validation even when the first matching element
appears to satisfy the rule.

------------------------------------------------------------------------

## FAIL

The live application does not match the expected production
configuration, or the expected element cannot be found.

Example:

``` text
Expected: True
Actual:   False
```

Result:

``` text
FAIL
```

Example note:

``` text
Logic Drift: Expected True, Found False
```

Another failure scenario:

``` text
Expected: True
Actual: NOT_FOUND
```

Result:

``` text
FAIL
```

Note:

``` text
Element not found in DOM.
```

------------------------------------------------------------------------

# 7. Intentional Drift Scenarios

The current POC intentionally contains configuration drift so that the
demo produces meaningful audit results.

For example, the configuration can expect:

``` text
disabled = True
```

while the live application contains:

``` text
disabled = False
```

The Judge identifies this as:

``` text
FAIL
Logic Drift: Expected True, Found False
```

This is intentional and demonstrates the core purpose of the
application.

------------------------------------------------------------------------

# 8. Duplicate ID Detection

The current target page contains a structural issue where multiple
elements share the same ID.

For example:

``` text
validationCustom05
```

appears more than once.

The Judge detects this and reports:

``` text
WARNING
ID Collision: 2 elements share this ID.
```

This is important because an automation or configuration auditor should
not blindly assume that an ID uniquely identifies a single DOM element.

------------------------------------------------------------------------

# 9. Missing Element Detection

The POC also demonstrates what happens when production configuration
references a field that does not exist in the live DOM.

Example:

``` text
validationCustom02
```

or another intentionally configured non-existent field.

The Judge reports:

``` text
Actual: NOT_FOUND
Status: FAIL
```

with:

``` text
Element not found in DOM.
```

This represents another form of configuration drift.

------------------------------------------------------------------------

# 10. Current Tenant Matrix

  -------------------------------------------------------------------------
  Tenant           Target                            Rules Purpose
                   Application
  ---------------- ----------------- --------------------- ----------------
  Practice_Bank    form-validation                       6 Bank
                                                           configuration
                                                           and intentional
                                                           drift

  Insurance_Demo   form-validation                       5 Insurance
                                                           configuration
                                                           and intentional
                                                           drift

  Retail_Demo      form-validation                       6 Retail
                                                           configuration
                                                           and intentional
                                                           drift
  -------------------------------------------------------------------------

The tenants currently use the same public practice application because
this is a POC.

In a production implementation, each tenant could point to its own
application or tenant-specific environment.

------------------------------------------------------------------------

# 11. Mock Production Configuration API

The mock API is implemented in:

``` text
mock_config_api.py
```

It uses FastAPI.

The configuration is currently stored in an in-memory structure:

``` python
TENANT_CONFIGS = {
    ...
}
```

This is intentionally simple for the POC.

A production implementation could replace this with:

-   PostgreSQL
-   MySQL
-   MongoDB
-   Configuration management service
-   Cloud configuration store
-   Internal REST API
-   Tenant metadata service

The Judge engine would not fundamentally need to change as long as the
configuration API returns the expected contract.

------------------------------------------------------------------------

# 12. Streamlit Dashboard

The web UI is implemented in:

``` text
judge_app.py
```

The dashboard provides:

-   Application title and description
-   Configuration API health indicator
-   Tenant selection
-   Configuration source display
-   Target application display
-   Configured audit-rule count
-   Run Audit button
-   PASS count
-   WARNING count
-   FAIL count
-   Detailed audit results
-   CSV report download

The UI converts the command-line POC into a demonstrable end-to-end
application.

------------------------------------------------------------------------

# 13. Dashboard Workflow

The normal demo workflow is:

``` text
Open The Judge
      |
      v
Select Tenant
      |
      v
Review Target Application
      |
      v
Click "Run Audit"
      |
      v
Judge Engine Executes
      |
      v
Configuration Retrieved
      |
      v
Live DOM Inspected
      |
      v
Expected vs Actual Compared
      |
      v
Dashboard Displays Results
      |
      v
Download CSV Report
```

------------------------------------------------------------------------

# 14. CSV Audit Reports

Audit reports are generated under:

``` text
audit_reports/
```

Examples:

``` text
drift_report_Practice_Bank.csv
drift_report_Insurance_Demo.csv
drift_report_Retail_Demo.csv
```

The report contains structured information such as:

  ---------------------------------------------------------------------------------
  Field ID             Check Type   Expected    Actual      Status      Notes
  -------------------- ------------ ----------- ----------- ----------- -----------
  validationCustom01   attribute    True        True        PASS        Matched

  validationCustom05   attribute    True        True        WARNING     ID
                                                                        collision

  validationCustom04   visibility   True        True        PASS        Matched

  validationCustom04   disabled     False       False       PASS        Matched

  validationCustom04   disabled     True        False       FAIL        Logic Drift

  validationCustom02   attribute    True        NOT_FOUND   FAIL        Element not
                                                                        found
  ---------------------------------------------------------------------------------

The CSV format allows the result to be consumed by other systems later.

Potential future consumers include:

-   Reporting dashboards
-   CI/CD pipelines
-   Test management systems
-   Defect management systems
-   Email notifications
-   Audit repositories

------------------------------------------------------------------------

# 15. Project Structure

Current project structure:

``` text
THE JUDGE/
│
├── .venv/
│
├── audit_reports/
│   ├── drift_report_Practice_Bank.csv
│   ├── drift_report_Insurance_Demo.csv
│   └── drift_report_Retail_Demo.csv
│
├── configs/
│
├── .env
│
├── inspect_form.py
├── judge_app.py
├── judge_engine.py
├── mock_config_api.py
├── README.md
├── requirements.txt
└── START_THE_JUDGE.bat
```

The `.venv` directory is the local Python virtual environment and should
not be committed to Git.

------------------------------------------------------------------------

# 16. Technologies Used

## Python

The core implementation language.

Used for:

-   Audit engine
-   DOM inspection
-   API integration
-   CSV generation
-   Streamlit dashboard

------------------------------------------------------------------------

## Playwright

Used for browser automation and live DOM inspection.

Main purpose:

``` text
Open application
        ↓
Locate DOM elements
        ↓
Read attributes/state
        ↓
Compare against configuration
```

------------------------------------------------------------------------

## FastAPI

Used to create the mock production configuration service.

It provides REST endpoints for:

-   Health check
-   Tenant listing
-   Tenant configuration retrieval

------------------------------------------------------------------------

## Uvicorn

Used to run the FastAPI application locally.

------------------------------------------------------------------------

## Streamlit

Used to create the dashboard UI.

The current project uses:

``` text
Streamlit 1.64.0
```

------------------------------------------------------------------------

## Pandas

Used for structured audit data and CSV processing.

------------------------------------------------------------------------

## Requests

Used by the dashboard/audit components for HTTP communication with the
configuration API where required.

------------------------------------------------------------------------

# 17. Installation

Create and activate the virtual environment.

Windows PowerShell:

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

``` powershell
pip install -r requirements.txt
```

Install the Playwright Chromium browser:

``` powershell
python -m playwright install chromium
```

### Important

`requirements.txt` installs the Python Playwright package.

It does **not** install the Chromium browser binary.

Therefore the Playwright browser installation is a separate setup step.

------------------------------------------------------------------------

# 18. Running The Judge Manually

The application consists of two local services:

``` text
FastAPI
   +
Streamlit
```

The FastAPI service provides configuration.

The Streamlit application provides the dashboard.

For development, the services can be started separately.

### Terminal 1 --- Configuration API

Activate the environment:

``` powershell
.\.venv\Scripts\Activate.ps1
```

Run:

``` powershell
uvicorn mock_config_api:app --reload --port 8000
```

The API becomes available at:

``` text
http://127.0.0.1:8000
```

------------------------------------------------------------------------

### Terminal 2 --- Streamlit

Activate the environment:

``` powershell
.\.venv\Scripts\Activate.ps1
```

Run:

``` powershell
streamlit run judge_app.py
```

Streamlit normally opens:

``` text
http://localhost:8501
```

------------------------------------------------------------------------

# 19. One-Click Demo

For demonstration purposes, the project includes:

``` text
START_THE_JUDGE.bat
```

The intention is to simplify the demo startup process.

Instead of manually opening multiple terminals, the BAT file starts the
required local components.

This is especially useful when demonstrating the project to:

-   Interviewers
-   Hiring managers
-   Engineering managers
-   QA leaders
-   Developers
-   Product teams

The goal is to make the POC feel like an application rather than a
collection of scripts.

------------------------------------------------------------------------

# 20. Command-Line Audit

The Streamlit UI is the primary presentation layer, but the underlying
engine can still be executed directly.

Example:

``` powershell
python judge_engine.py Practice_Bank
```

Example:

``` powershell
python judge_engine.py Insurance_Demo
```

Example:

``` powershell
python judge_engine.py Retail_Demo
```

This is useful for:

-   Debugging
-   Development
-   CI/CD integration
-   Automation
-   Troubleshooting

------------------------------------------------------------------------

# 21. DOM Inspection Utility

The project also contains:

``` text
inspect_form.py
```

Run:

``` powershell
python inspect_form.py
```

This utility helps identify the real fields and attributes present on
the target page.

It was used to build the initial audit configuration from actual DOM
information.

This is important because the audit rules should ideally represent real
application configuration rather than arbitrary test data.

------------------------------------------------------------------------

# 22. Example Audit Result

A typical Practice_Bank run can produce:

``` text
Total Rules : 6
PASS        : 3
WARNING     : 1
FAIL        : 2
```

Example interpretation:

``` text
3 rules match the live application.

1 rule identified a structural warning:
duplicate DOM ID.

2 rules identified configuration drift:
one expected state does not match the live state,
and one configured element is missing from the DOM.
```

The dashboard displays the same information visually.

------------------------------------------------------------------------

# 23. Why Multi-Tenant Configuration Matters

A major design goal of The Judge is separating:

``` text
Audit Engine
```

from:

``` text
Tenant Configuration
```

The audit engine should not contain hard-coded business rules for every
customer.

Instead:

``` text
Tenant
  |
  +--> Configuration
  |
  +--> Audit Rules
  |
  +--> Target Application
```

The same engine can then process:

``` text
Practice_Bank
Insurance_Demo
Retail_Demo
```

using different configuration data.

This is the foundation for scaling the concept to a larger multi-tenant
SaaS environment.

------------------------------------------------------------------------

# 24. Architectural Separation

The current POC demonstrates three logical layers.

## Layer 1 --- Configuration

``` text
mock_config_api.py
```

Responsible for:

-   Tenant configuration
-   Target URL
-   Audit rules

------------------------------------------------------------------------

## Layer 2 --- Audit Engine

``` text
judge_engine.py
```

Responsible for:

-   Browser interaction
-   DOM inspection
-   Rule execution
-   Comparison
-   Status calculation
-   Report generation

------------------------------------------------------------------------

## Layer 3 --- Presentation

``` text
judge_app.py
```

Responsible for:

-   Tenant selection
-   Audit execution
-   Result presentation
-   Metrics
-   CSV download

This separation makes the POC easier to evolve.

------------------------------------------------------------------------

# 25. Design Philosophy

The Judge follows a simple principle:

> **Configuration is the expected state. The live application is the
> actual state. The Judge compares the two.**

Conceptually:

``` text
Expected Configuration
          |
          v
       THE JUDGE
          ^
          |
      Actual DOM
```

The output is:

``` text
PASS
WARNING
FAIL
```

This makes configuration drift visible and measurable.

------------------------------------------------------------------------

# 26. Current POC Scope

The current implementation intentionally focuses on a small,
demonstrable scope.

It currently demonstrates:

-   Multi-tenant configuration
-   REST configuration retrieval
-   Browser automation
-   DOM inspection
-   Attribute validation
-   Visibility validation
-   Disabled-state validation
-   Missing-element detection
-   Duplicate-ID detection
-   Configuration drift detection
-   CSV reporting
-   Streamlit dashboard
-   One-click local startup

The target application is currently a public practice form.

The configuration API is currently a local mock service.

Therefore, this repository should be considered a **POC**, not a
production-ready enterprise implementation.

------------------------------------------------------------------------

# 27. Future Enhancements

The architecture can be extended in several directions.

## Real Configuration Database

Replace the in-memory configuration:

``` python
TENANT_CONFIGS = {...}
```

with a database or external configuration service.

------------------------------------------------------------------------

## More Audit Rule Types

Possible future checks:

``` text
attribute
attribute_value
visibility
disabled
text
placeholder
input_type
value
class
CSS property
ARIA attribute
element count
DOM structure
```

------------------------------------------------------------------------

## Authentication

Add authentication and authorization for:

-   Administrators
-   QA users
-   Tenant users
-   Auditors

------------------------------------------------------------------------

## Scheduled Audits

Run audits automatically:

``` text
Hourly
Daily
Before deployment
After deployment
On configuration change
```

------------------------------------------------------------------------

## CI/CD Integration

The Judge could be integrated into:

``` text
GitHub Actions
Jenkins
GitLab CI
Azure DevOps
```

For example:

``` text
Deployment
    |
    v
The Judge Audit
    |
    +---- PASS ----> Continue pipeline
    |
    +---- FAIL ----> Stop / Alert
```

------------------------------------------------------------------------

## Historical Audit Results

Store every audit run so the system can show:

``` text
Tenant
Timestamp
Rules checked
PASS
WARNING
FAIL
Previous result
Current result
```

This would allow configuration drift trends to be tracked over time.

------------------------------------------------------------------------

## Notifications

Future integrations could include:

-   Email
-   Slack
-   Microsoft Teams
-   Jira
-   ServiceNow

------------------------------------------------------------------------

## Production Browser Grid

For large-scale use, browser execution could be moved to:

-   Playwright workers
-   Browser containers
-   Selenium Grid
-   Cloud browser infrastructure

------------------------------------------------------------------------

# 28. Security Considerations for a Production Version

The current POC is local and intentionally simple.

A production implementation should address:

-   API authentication
-   Tenant isolation
-   Secrets management
-   HTTPS
-   Role-based access control
-   Audit-log integrity
-   Credential rotation
-   Secure browser execution
-   Network restrictions
-   Sensitive configuration handling

The mock configuration API should not be treated as a secure production
configuration service.

------------------------------------------------------------------------

# 29. Troubleshooting

## Streamlit command not found

Activate the virtual environment:

``` powershell
.\.venv\Scripts\Activate.ps1
```

Then verify:

``` powershell
pip show streamlit
```

Run:

``` powershell
streamlit run judge_app.py
```

------------------------------------------------------------------------

## Playwright browser not installed

Run:

``` powershell
python -m playwright install chromium
```

------------------------------------------------------------------------

## Configuration API unavailable

Verify the FastAPI service is running:

``` powershell
uvicorn mock_config_api:app --reload --port 8000
```

Then check:

``` text
http://127.0.0.1:8000/health
```

------------------------------------------------------------------------

## Audit cannot open target application

Check:

-   Internet connectivity
-   Target URL
-   Playwright Chromium installation
-   Browser compatibility
-   Target application availability

------------------------------------------------------------------------

# 30. Git and Repository Hygiene

The following local/generated content should normally not be committed:

``` text
.venv/
__pycache__/
*.pyc
.env
```

Generated audit reports may also be excluded depending on the repository
strategy.

The repository should contain the source code and documentation required
to reproduce the POC rather than local environment files.

------------------------------------------------------------------------

# 31. Recommended Demo Flow

For an interview or technical demonstration, use the following sequence.

### Step 1

Start The Judge using:

``` text
START_THE_JUDGE.bat
```

### Step 2

Open the Streamlit dashboard.

### Step 3

Show the tenant selector.

Explain:

``` text
The Judge is multi-tenant.
Each tenant gets its own configuration and audit rules.
```

### Step 4

Select:

``` text
Practice_Bank
```

### Step 5

Click:

``` text
Run Audit
```

### Step 6

Show:

``` text
PASS
WARNING
FAIL
```

### Step 7

Explain one PASS:

``` text
Expected required=True
Actual required=True
```

### Step 8

Explain the WARNING:

``` text
Duplicate ID detected.
```

### Step 9

Explain the FAIL:

``` text
Expected disabled=True
Actual disabled=False
```

### Step 10

Explain the missing-field failure:

``` text
Configuration expects an element that does not exist in the live DOM.
```

### Step 11

Download the CSV report.

This demonstrates the complete lifecycle:

``` text
Configuration
      ↓
API
      ↓
Audit Engine
      ↓
Playwright
      ↓
Live DOM
      ↓
Comparison
      ↓
Dashboard
      ↓
CSV Report
```

------------------------------------------------------------------------

# 32. Project Status

Current status:

``` text
[x] Mock production configuration API
[x] Multi-tenant configuration
[x] Real DOM inspection
[x] Audit engine
[x] PASS detection
[x] WARNING detection
[x] FAIL detection
[x] Duplicate ID detection
[x] Missing element detection
[x] Configuration drift detection
[x] CSV reporting
[x] Streamlit dashboard
[x] Tenant selection
[x] One-click startup
[x] Basic documentation
```

The project is currently at the **POC / demonstrable prototype stage**.

------------------------------------------------------------------------

# 33. Conclusion

The Judge demonstrates how a configuration-driven auditing engine can
validate a live application's actual state against tenant-specific
expected configuration.

The core concept is simple:

``` text
EXPECTED
   |
   |  Compare
   v
THE JUDGE
   ^
   |  Inspect
   |
ACTUAL
```

The current POC combines:

``` text
Python
FastAPI
Playwright
Pandas
Streamlit
CSV Reporting
```

into one end-to-end demonstration.

The architecture is intentionally designed so that the current mock
components can later be replaced by real enterprise services without
changing the fundamental audit concept.

------------------------------------------------------------------------

## Author / Project

**The Judge --- Multi-Tenant Configuration Drift Auditor**

Technology stack:

``` text
Python
FastAPI
Playwright
Pandas
Streamlit
Pytest
```

Status:
``` text
Proof of Concept
```
