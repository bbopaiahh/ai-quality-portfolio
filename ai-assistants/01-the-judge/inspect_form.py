from playwright.sync_api import sync_playwright


TARGET_URL = "https://practice.expandtesting.com/form-validation"


with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    print(f"\nOpening: {TARGET_URL}")

    page.goto(
        TARGET_URL,
        wait_until="load",
        timeout=30000
    )

    print("\n" + "=" * 80)
    print("THE JUDGE - DOM CONFIGURATION INSPECTOR")
    print("=" * 80)

    elements = page.locator(
        "input, select, textarea, button"
    )

    count = elements.count()

    print(f"\nFound {count} form elements.\n")

    for index in range(count):

        element = elements.nth(index)

        tag_name = element.evaluate(
            "el => el.tagName.toLowerCase()"
        )

        element_id = element.get_attribute("id")

        element_name = element.get_attribute("name")

        element_type = element.get_attribute("type")

        required = element.get_attribute("required")

        maxlength = element.get_attribute("maxlength")

        minlength = element.get_attribute("minlength")

        disabled = element.is_disabled()

        visible = element.is_visible()

        value = element.get_attribute("value")

        print("-" * 80)

        print(f"Element #{index + 1}")

        print(f"Tag        : {tag_name}")
        print(f"ID         : {element_id}")
        print(f"Name       : {element_name}")
        print(f"Type       : {element_type}")
        print(f"Required   : {required}")
        print(f"Max Length : {maxlength}")
        print(f"Min Length : {minlength}")
        print(f"Disabled   : {disabled}")
        print(f"Visible    : {visible}")
        print(f"Value      : {value}")

    print("\n" + "=" * 80)
    print("DOM INSPECTION COMPLETE")
    print("=" * 80)

    input("\nPress ENTER to close the browser...")

    browser.close()