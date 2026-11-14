from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="The Judge Mock Configuration API",
    description="Mock production configuration service for The Judge POC",
    version="1.0.0"
)


# =========================================================
# Mock Production Configuration
# =========================================================

TENANT_CONFIGS = {

    # =====================================================
    # PRACTICE BANK
    # =====================================================

    "Practice_Bank": {

        "tenant": "Practice_Bank",

        "target_url": "https://practice.expandtesting.com/form-validation",

        "audit_rules": [

            # -------------------------------------------------
            # PASS - Required attribute exists
            # -------------------------------------------------
            {
                "id": "validationCustom01",
                "check": "attribute",
                "property": "required",
                "expected": True
            },

            # -------------------------------------------------
            # WARNING - Duplicate ID
            # validationCustom05 exists twice in the DOM
            # -------------------------------------------------
            {
                "id": "validationCustom05",
                "check": "attribute",
                "property": "required",
                "expected": True
            },

            # -------------------------------------------------
            # PASS - Element is visible
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "visibility",
                "expected": True
            },

            # -------------------------------------------------
            # PASS - Element is enabled
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "disabled",
                "expected": False
            },

            # -------------------------------------------------
            # FAIL - Intentional configuration drift
            #
            # Application:
            # disabled = False
            #
            # Configuration:
            # disabled = True
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "disabled",
                "expected": True
            },

            # -------------------------------------------------
            # FAIL - Field does not exist in DOM
            # -------------------------------------------------
            {
                "id": "validationCustom02",
                "check": "attribute",
                "property": "required",
                "expected": True
            }
        ]
    },


    # =====================================================
    # INSURANCE DEMO
    # =====================================================

    "Insurance_Demo": {

        "tenant": "Insurance_Demo",

        "target_url": "https://practice.expandtesting.com/form-validation",

        "audit_rules": [

            # -------------------------------------------------
            # Contact Name must be required
            # -------------------------------------------------
            {
                "id": "validationCustom01",
                "check": "attribute",
                "property": "required",
                "expected": True
            },

            # -------------------------------------------------
            # Contact Number configuration
            #
            # validationCustom05 exists twice.
            # Therefore Judge can detect ID collision.
            # -------------------------------------------------
            {
                "id": "validationCustom05",
                "check": "attribute",
                "property": "required",
                "expected": True
            },

            # -------------------------------------------------
            # Payment Method must be visible
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "visibility",
                "expected": True
            },

            # -------------------------------------------------
            # Payment Method should be enabled
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "disabled",
                "expected": False
            },

            # -------------------------------------------------
            # FAIL - Intentional Insurance configuration drift
            #
            # Application:
            # disabled = False
            #
            # Insurance configuration:
            # disabled = True
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "disabled",
                "expected": True
            }
        ]
    },


    # =====================================================
    # RETAIL DEMO
    # =====================================================

    "Retail_Demo": {

        "tenant": "Retail_Demo",

        "target_url": "https://practice.expandtesting.com/form-validation",

        "audit_rules": [

            # -------------------------------------------------
            # Contact Name must be required
            # -------------------------------------------------
            {
                "id": "validationCustom01",
                "check": "attribute",
                "property": "required",
                "expected": True
            },

            # -------------------------------------------------
            # Pickup Date configuration
            #
            # validationCustom05 is also used by the
            # contact-number field, creating a duplicate ID.
            # -------------------------------------------------
            {
                "id": "validationCustom05",
                "check": "attribute",
                "property": "required",
                "expected": True
            },

            # -------------------------------------------------
            # Payment Method must be visible
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "visibility",
                "expected": True
            },

            # -------------------------------------------------
            # Payment Method should NOT be disabled
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "disabled",
                "expected": False
            },

            # -------------------------------------------------
            # FAIL - Intentional Retail configuration drift
            #
            # Application:
            # disabled = False
            #
            # Retail configuration:
            # disabled = True
            # -------------------------------------------------
            {
                "id": "validationCustom04",
                "check": "disabled",
                "expected": True
            },

            # -------------------------------------------------
            # FAIL - Field does not exist in DOM
            # -------------------------------------------------
            {
                "id": "validationCustom99",
                "check": "visibility",
                "expected": True
            }
        ]
    }
}


# =========================================================
# Health Check
# =========================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "The Judge Mock Configuration API"
    }


# =========================================================
# Tenant Configuration Endpoint
# =========================================================

@app.get("/api/tenants/{tenant}/config")
def get_tenant_config(tenant: str):

    if tenant not in TENANT_CONFIGS:

        raise HTTPException(
            status_code=404,
            detail=f"Tenant '{tenant}' not found"
        )

    return TENANT_CONFIGS[tenant]


# =========================================================
# List Available Tenants
# =========================================================

@app.get("/api/tenants")
def list_tenants():

    return {
        "tenants": list(TENANT_CONFIGS.keys())
    }