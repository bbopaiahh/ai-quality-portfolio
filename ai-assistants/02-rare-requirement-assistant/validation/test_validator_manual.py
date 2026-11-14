from validation.test_case_validator import TestCaseValidator


test_cases = [
    {
        "Test Case ID": "TC001",
        "Module": "Lead Management",
        "Scenario": "Create a valid lead",
        "Test Steps": (
            "1. Open Lead Management<br>"
            "2. Enter valid lead details<br>"
            "3. Click Save"
        ),
        "Expected Result": (
            "Lead is saved successfully."
        ),
        "Priority": "P1",
        "Type": "Positive Case",
        "Suite Type": "Smoke",
        "Automation Type": "UI Automation",
    }
]


validator = TestCaseValidator()

result = validator.validate(test_cases)

print("VALID:", result.is_valid)
print("ERRORS:", result.errors)
print("WARNINGS:", result.warnings)