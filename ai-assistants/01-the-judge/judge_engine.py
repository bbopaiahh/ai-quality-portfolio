import sys
import json
import os
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
from datetime import datetime


class JudgeEngine:

    def __init__(self, config_path=None, tenant="Practice_Bank"):
        self.config_path = config_path
        self.tenant = tenant

        self.config_api_url = (
            f"http://127.0.0.1:8000/api/tenants/{self.tenant}/config"
        )

        self.rules = {}
        self.report_data = []

        # Ensure the output directory exists
        self.output_dir = "audit_reports"

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    # ---------------------------------------------------------
    # LOAD CONFIGURATION FROM MOCK PRODUCTION API
    # ---------------------------------------------------------

    def load_json_truth(self):

        try:
            print(
                "\n--- Retrieving configuration from Mock Production API ---"
            )

            print(f"API: {self.config_api_url}")

            response = requests.get(
                self.config_api_url,
                timeout=10
            )

            response.raise_for_status()

            self.rules = response.json()

            print(
                f"\n--- Configuration Loaded for Tenant: "
                f"{self.rules.get('tenant')} ---"
            )

            return True

        except requests.RequestException as api_error:

            print(
                f"\n[WARNING] Mock Production API unavailable: "
                f"{api_error}"
            )

            # -------------------------------------------------
            # FALLBACK TO LOCAL JSON CONFIGURATION
            # -------------------------------------------------

            if self.config_path and os.path.exists(self.config_path):

                print(
                    "[INFO] Falling back to local JSON configuration."
                )

                with open(self.config_path, "r") as file:
                    self.rules = json.load(file)

                print(
                    f"--- Local Configuration Loaded for Tenant: "
                    f"{self.rules.get('tenant')} ---"
                )

                return True

            print(
                "[ERROR] No API configuration and no local "
                "fallback available."
            )

            return False

    # ---------------------------------------------------------
    # RULE EVALUATION ENGINE
    # ---------------------------------------------------------

    def evaluate_rule(self, target_element, rule):

        check_type = rule.get("check", "attribute")
        property_name = rule.get("property")
        expected_value = rule.get("expected")

        # -----------------------------------------------------
        # 1. ATTRIBUTE EXISTENCE
        # -----------------------------------------------------

        if check_type == "attribute":

            actual_value = target_element.evaluate(
                f"el => el.hasAttribute('{property_name}')"
            )

            passed = (
                str(actual_value).lower()
                == str(expected_value).lower()
            )

            return actual_value, passed

        # -----------------------------------------------------
        # 2. ATTRIBUTE VALUE
        # -----------------------------------------------------

        elif check_type == "attribute_value":

            actual_value = target_element.get_attribute(
                property_name
            )

            if actual_value is not None:

                try:

                    if isinstance(expected_value, int):
                        actual_value = int(actual_value)

                    elif isinstance(expected_value, float):
                        actual_value = float(actual_value)

                except (ValueError, TypeError):
                    pass

            passed = actual_value == expected_value

            return actual_value, passed

        # -----------------------------------------------------
        # 3. VISIBILITY
        # -----------------------------------------------------

        elif check_type == "visibility":

            actual_value = target_element.is_visible()

            passed = actual_value == expected_value

            return actual_value, passed

        # -----------------------------------------------------
        # 4. DISABLED
        # -----------------------------------------------------

        elif check_type == "disabled":

            actual_value = target_element.is_disabled()

            passed = actual_value == expected_value

            return actual_value, passed

        # -----------------------------------------------------
        # UNSUPPORTED CHECK TYPE
        # -----------------------------------------------------

        else:

            raise ValueError(
                f"Unsupported audit check type: {check_type}"
            )

    # ---------------------------------------------------------
    # RUN AUDIT
    # ---------------------------------------------------------

    def run_audit(self):

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False
            )

            page = browser.new_page()

            target_url = self.rules.get("target_url")

            print(
                f"Navigating to: {target_url}"
            )

            try:

                page.goto(
                    target_url,
                    wait_until="load",
                    timeout=30000
                )

            except Exception as navigation_error:

                print(
                    "Warning: Navigation timeout reached, "
                    "but proceeding..."
                )

                print(
                    f"Navigation details: {navigation_error}"
                )

            # -------------------------------------------------
            # PROCESS EACH AUDIT RULE
            # -------------------------------------------------

            for rule in self.rules.get(
                "audit_rules",
                []
            ):

                field_id = rule.get("id")
                expected_val = rule.get("expected")
                check_type = rule.get(
                    "check",
                    "attribute"
                )
                property_name = rule.get("property")

                print(
                    f"Auditing Field: {field_id} "
                    f"[{check_type}]..."
                )

                all_matches = page.locator(
                    f"#{field_id}"
                )

                match_count = all_matches.count()

                status = "PASS"
                actual_val = "NOT_FOUND"
                verdict = "Matched"

                # -------------------------------------------------
                # ELEMENT FOUND
                # -------------------------------------------------

                if match_count > 0:

                    target_element = all_matches.first

                    try:

                        actual_val, passed = self.evaluate_rule(
                            target_element,
                            rule
                        )

                        # -----------------------------------------
                        # RULE FAILED
                        # -----------------------------------------

                        if not passed:

                            status = "FAIL"

                            verdict = (
                                f"Logic Drift: "
                                f"Expected {expected_val}, "
                                f"Found {actual_val}"
                            )

                        # -----------------------------------------
                        # DUPLICATE ID
                        # -----------------------------------------

                        elif match_count > 1:

                            status = "WARNING"

                            verdict = (
                                f"ID Collision: "
                                f"{match_count} elements "
                                f"share this ID."
                            )

                    except ValueError as rule_error:

                        status = "FAIL"

                        actual_val = "ERROR"

                        verdict = str(rule_error)

                    except Exception as evaluation_error:

                        status = "FAIL"

                        actual_val = "ERROR"

                        verdict = (
                            f"Rule evaluation error: "
                            f"{evaluation_error}"
                        )

                # -------------------------------------------------
                # ELEMENT NOT FOUND
                # -------------------------------------------------

                else:

                    status = "FAIL"

                    verdict = (
                        "Element not found in DOM."
                    )

                # -------------------------------------------------
                # STORE RESULT
                # -------------------------------------------------

                self.report_data.append({

                    "Timestamp":
                        datetime.now().strftime(
                            "%H:%M:%S"
                        ),

                    "Field_ID":
                        field_id,

                    "Check":
                        check_type,

                    "Rule":
                        property_name,

                    "Expected":
                        expected_val,

                    "Actual":
                        actual_val,

                    "Status":
                        status,

                    "Notes":
                        verdict
                })

            browser.close()

    # ---------------------------------------------------------
    # GENERATE CSV REPORT
    # ---------------------------------------------------------

    def generate_report(self):

        df = pd.DataFrame(self.report_data)

        # ---------------------------------------------------------
        # Add tenant information to every audit record
        # ---------------------------------------------------------

        df.insert(
            0,
            "Tenant",
            self.rules.get("tenant", self.tenant)
        )

        # ---------------------------------------------------------
        # Rename columns for professional audit reporting
        # ---------------------------------------------------------

        df.rename(
            columns={
                "Check": "Check_Type",
                "Rule": "Property"
            },
            inplace=True
        )

        # ---------------------------------------------------------
        # Define professional column order
        # ---------------------------------------------------------

        report_columns = [
            "Tenant",
            "Timestamp",
            "Field_ID",
            "Check_Type",
            "Property",
            "Expected",
            "Actual",
            "Status",
            "Notes"
        ]

        df = df[report_columns]

        # ---------------------------------------------------------
        # Console Summary
        # ---------------------------------------------------------

        print("\n" + "=" * 70)
        print("THE JUDGE: FINAL AUDIT VERDICT")
        print("=" * 70)

        print(
            df[
                [
                    "Field_ID",
                    "Check_Type",
                    "Expected",
                    "Actual",
                    "Status",
                    "Notes"
                ]
            ].to_string(index=False)
        )

        # ---------------------------------------------------------
        # Audit Summary
        # ---------------------------------------------------------

        total_rules = len(df)

        pass_count = (
            (df["Status"] == "PASS").sum()
        )

        warning_count = (
            (df["Status"] == "WARNING").sum()
        )

        fail_count = (
            (df["Status"] == "FAIL").sum()
        )

        print("\n" + "-" * 70)
        print("AUDIT SUMMARY")
        print("-" * 70)

        print(f"Tenant        : {self.rules.get('tenant', self.tenant)}")
        print(f"Total Rules   : {total_rules}")
        print(f"PASS          : {pass_count}")
        print(f"WARNING       : {warning_count}")
        print(f"FAIL          : {fail_count}")

        # ---------------------------------------------------------
        # Save CSV
        # ---------------------------------------------------------

        report_name = (
            f"drift_report_"
            f"{self.rules.get('tenant', self.tenant)}.csv"
        )

        full_path = os.path.join(
            self.output_dir,
            report_name
        )

        df.to_csv(
            full_path,
            index=False
        )

        print("\n" + "-" * 70)

        print(
            f"[SUCCESS] Audit Complete."
        )

        print(
            f"Results saved to: {full_path}"
        )

        print("-" * 70)


# =============================================================
# APPLICATION ENTRY POINT
# =============================================================

if __name__ == "__main__":

    # ---------------------------------------------------------
    # Read tenant from command line
    # ---------------------------------------------------------

    tenant = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Practice_Bank"
    )

    print(
        f"\n--- Starting The Judge for Tenant: {tenant} ---"
    )

    judge = JudgeEngine(

        config_path="configs/tenant_audit.json",

        tenant=tenant
    )

    if judge.load_json_truth():

        judge.run_audit()

        judge.generate_report()