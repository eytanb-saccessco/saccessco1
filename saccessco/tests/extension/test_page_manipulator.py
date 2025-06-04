# saccessco/tests/extension/test_page_manipulator.py
import time
import json
import logging  # Import logging

from django.urls import reverse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from django.conf import settings  # Import settings to access BASE_DIR

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

# Set up a logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all messages

# Define paths to the JavaScript files (assuming 'saccessco' is a Django app within BASE_DIR)
CHAT_MODULE_JS_PATH = settings.BASE_DIR / 'static' / 'js' / 'chrome_extension' / 'chat_module.js'
PAGE_MANIPULATOR_JS_PATH = settings.BASE_DIR / 'static' / 'js' / 'chrome_extension' / 'page_manipulator.js'


class PageManipulatorTest(AbstractExtensionPageTest):
    # CRITICAL FIX: Override JS_FILES from AbstractExtensionPageTest to prevent
    # automatic injection of chat_module.js and page_manipulator.js before navigation.
    # This ensures they are only injected once, after the driver.get() call.
    # If AbstractExtensionPageTest needs other JS files, list them here,
    # but EXCLUDE chat_module.js and page_manipulator.js.
    JS_FILES = []  # This is the crucial line to prevent parent injection

    def setUp(self):
        # Call super().setUp() FIRST to initialize the live server and basic browser setup.
        # With JS_FILES = [], this should now NOT inject chat_module.js or page_manipulator.js.
        super().setUp()

        # Navigate to the test page. This will clear any previously loaded JS context.
        self.driver.get(self.live_server_url + reverse('test_page_manipulator'))

        # Now, explicitly inject the necessary JavaScript files into the current page context.
        # This ensures they are loaded AFTER the page itself has loaded and its JS context is fresh.
        try:
            with open(PAGE_MANIPULATOR_JS_PATH, 'r') as f:
                page_manipulator_js_content = f.read()
            logger.debug(f"Read page_manipulator.js content length: {len(page_manipulator_js_content)}")
            self.driver.execute_script(page_manipulator_js_content)
            print("INFO: Injected page_manipulator.js into the page.")
        except Exception as e:
            self.fail(f"Failed to read or inject page_manipulator.js: {e}")

        try:
            with open(CHAT_MODULE_JS_PATH, 'r') as f:
                chat_module_js_content = f.read()
            logger.debug(f"Read chat_module.js content length: {len(chat_module_js_content)}")
            self.driver.execute_script(chat_module_js_content)
            print("INFO: Injected chat_module.js into the page.")
        except Exception as e:
            self.fail(f"Failed to read or inject chat_module.js: {e}")

        # Give a very brief moment for scripts to execute after injection
        time.sleep(0.05)  # 50 milliseconds

        # Wait for page_manipulatorModule to be available
        try:
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return typeof window.pageManipulatorModule !== 'undefined';")
            )
            print("INFO: pageManipulatorModule is available in the browser.")
        except TimeoutException:
            browser_logs = self.driver.get_log('browser')
            print("\n--- BROWSER CONSOLE LOGS (during pageManipulatorModule wait timeout) ---")
            for entry in browser_logs:
                print(entry)
            print("-------------------------------------------------------------------------")
            self.fail("Timed out waiting for window.pageManipulatorModule to be defined.")

        # Wait for chatModule to be available before mocking it
        try:
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script("return typeof window.chatModule !== 'undefined';")
            )
            print("INFO: chatModule is available in the browser.")
        except TimeoutException:
            browser_logs = self.driver.get_log('browser')
            print("\n--- BROWSER CONSOLE LOGS (during chatModule wait timeout) ---")
            for entry in browser_logs:
                print(entry)
            print("-------------------------------------------------------------------------")
            self.fail("Timed out waiting for window.chatModule to be defined before mocking.")

        # Mock chatModule.askConfirmation for sensitive input tests
        self.driver.execute_script("""
            window.__mockConfirmationResult = true; // Default to true for most tests
            window.chatModule.askConfirmation = async function(prompt) {
                console.log("GLOBAL STUB: chatModule.askConfirmation called with:", prompt);
                // Use a global variable to control the mock's return value
                return Promise.resolve(window.__mockConfirmationResult);
            };
            console.log("INFO: Specific chatModule.askConfirmation mock re-injected with prompt-aware logic.");
        """)

    def _execute_plan_and_get_result(self, plan):
        """Helper to execute plan and handle potential None result from execute_script."""
        print(f"DEBUG: Executing plan from Python: {json.dumps(plan)}")

        # Ensure pageManipulatorModule is available before executing the plan
        try:
            WebDriverWait(self.driver, 5).until(
                lambda driver: driver.execute_script(
                    "return typeof window.pageManipulatorModule !== 'undefined' && typeof window.pageManipulatorModule.executePlan === 'function';"
                )
            )
        except TimeoutException:
            browser_logs = self.driver.get_log('browser')
            print("\n--- BROWSER CONSOLE LOGS (during _execute_plan_and_get_result pre-check timeout) ---")
            for entry in browser_logs:
                print(entry)
            print("-------------------------------------------------------------------------")
            self.fail(
                f"Timed out waiting for window.pageManipulatorModule.executePlan to be defined before executing plan: {json.dumps(plan)}"
            )

        result = self.driver.execute_script("return await window.pageManipulatorModule.executePlan(arguments[0]);",
                                            plan)
        if result is None:
            browser_logs = self.driver.get_log('browser')
            print("\n--- BROWSER CONSOLE LOGS (during _execute_plan_and_get_result None return) ---")
            for entry in browser_logs:
                print(entry)
            print("-------------------------------------------------------------------------")
            self.fail(f"pageManipulatorModule.executePlan returned None for plan: {json.dumps(plan)}")
        return result

    def _inject_and_reset_test_harness(self):
        """
        Injects test-specific flags and event listeners into the browser
        and resets element states.
        This function should be called at the beginning of each test method.
        """
        # --- CRITICAL FIX: Wait for the body to be present, then a small sleep for rendering ---
        wait = WebDriverWait(self.driver, 10)  # Increased timeout to 10 seconds for robustness
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body"))), "Body element not present"
        time.sleep(0.5)  # Add a small fixed delay to allow full rendering after initial presence

        self.driver.execute_script("""
            // Define global flags for testing interactions
            window.__buttonClicked = false;
            window.__formSubmitted = false;
            window.__formSubmitted2 = false;
            window.__enterPressed = false;
            window.__passwordSet = false;
            window.__userInputText = '';

            // Add event listeners dynamically
            // It's safer to check if elements exist before adding listeners,
            // even though we're waiting in Python, it's good practice for JS robustness.
            const clickBtn = document.getElementById('clickButton');
            if (clickBtn) clickBtn.addEventListener('click', function() {
                window.__buttonClicked = true;
                console.log('Test Harness: Button was clicked!');
            }, { once: true }); // Use { once: true } to ensure it only fires once per test

            const passwordInput = document.getElementById('passwordInput');
            if (passwordInput) passwordInput.addEventListener('input', function() {
                window.__passwordSet = true;
                console.log('Test Harness: Password input detected!');
            }, { once: true });

            const textInput = document.getElementById('textInput');
            if (textInput) {
                textInput.addEventListener('input', function(event) {
                    window.__userInputText = event.target.value;
                    console.log('Test Harness: Text input detected, value:', window.__userInputText);
                });
                textInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        window.__enterPressed = true;
                        console.log('Test Harness: Enter keypress detected!');
                    }
                }, { once: true });
            }

            const testForm = document.getElementById('testForm');
            if (testForm) testForm.addEventListener('submit', function(event) {
                event.preventDefault(); // Prevent actual form submission
                window.__formSubmitted = true;
                console.log('Test Harness: Form 1 submitted!');
            }); // REMOVED { once: true }

            const testForm2 = document.getElementById('testForm2');
            // Listener on form, not button, as submit event bubbles up to the form
            if (testForm2) testForm2.addEventListener('submit', function(event) {
                event.preventDefault(); // Prevent actual form submission
                window.__formSubmitted2 = true;
                console.log('Test Harness: Form 2 submitted!');
            }); // REMOVED { once: true }

            // Reset initial values of elements for a clean state
            // These should also be checked for existence before manipulation
            const resetTextInput = document.getElementById('textInput');
            if (resetTextInput) resetTextInput.value = 'Initial Value';

            const resetPasswordInput = document.getElementById('passwordInput');
            if (resetPasswordInput) resetPasswordInput.value = '';

            const resetCheckboxInput = document.getElementById('checkboxInput');
            if (resetCheckboxInput) resetCheckboxInput.checked = true;

            const resetRadio1 = document.getElementById('radio1');
            if (resetRadio1) resetRadio1.checked = false;

            const resetRadio2 = document.getElementById('radio2');
            if (resetRadio2) resetRadio2.checked = true;

            const resetSelectDropdown = document.getElementById('selectDropdown');
            if (resetSelectDropdown) resetSelectDropdown.value = 'opt0';

            const resetFormInput1 = document.getElementById('formInput1');
            if (resetFormInput1) resetFormInput1.value = 'default form data';

            const resetFormInput2 = document.getElementById('formInput2');
            if (resetFormInput2) resetFormInput2.value = 'another form data';

            const resetContentEditableDiv = document.getElementById('contentEditableDiv');
            if (resetContentEditableDiv) resetContentEditableDiv.textContent = 'This is editable content.';

            console.log("INFO: Test harness (flags and listeners) injected and elements reset.");
        """)
        # Give a very brief moment for the browser to process the injection and reset
        time.sleep(0.1)

    def test_focus_action(self):
        print("\n--- Running test_focus_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "textInput"))
        )
        plan = [{"action": "focus", "selector": "#textInput"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for focus action.")
        self.assertTrue(result["results"][0]["success"], "Focus action should be successful.")

        is_focused = self.driver.execute_script("return document.activeElement.id === 'textInput';")
        self.assertTrue(is_focused, "Input field should be focused after action.")
        print("SUCCESS: Focus action verified.")

    def test_enter_value_action(self):
        print("\n--- Running test_enter_value_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        text_input_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "textInput"))
        )
        test_value = "Hello World"
        plan = [{"action": "enter_value", "element": "#textInput", "data": test_value}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for enter_value action.")
        self.assertTrue(result["results"][0]["success"], "Enter value action should be successful.")

        # Directly assert on the input field's value
        WebDriverWait(self.driver, 5).until(
            EC.text_to_be_present_in_element_value((By.ID, "textInput"), test_value),
            message=f"Timeout waiting for textInput value to be '{test_value}'."
        )
        input_value = text_input_element.get_attribute('value')
        self.assertEqual(input_value, test_value, "Input field value should be updated.")
        print("SUCCESS: Enter value action verified.")

    def test_click_action(self):
        print("\n--- Running test_click_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "clickButton"))
        )
        plan = [{"action": "click", "selector": "#clickButton"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for click action.")
        self.assertTrue(result["results"][0]["success"], "Click action should be successful.")

        # Explicitly wait for the flag to be set by the HTML's click event listener
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script("return window.__buttonClicked === true;"),
            message="Timeout waiting for __buttonClicked to be true."
        )
        button_clicked = self.driver.execute_script("return window.__buttonClicked;")
        self.assertTrue(button_clicked, "Button should have been clicked.")
        print("SUCCESS: Click action verified.")

    def test_submit_action_on_form(self):
        print("\n--- Running test_submit_action_on_form ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, "testForm"))
        )
        plan = [{"action": "submit_form", "selector": "#testForm"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for submit action.")
        self.assertTrue(result["results"][0]["success"], "Submit form action should be successful.")

        # Explicitly wait for the flag to be set by the HTML's submit event listener
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script("return window.__formSubmitted === true;"),
            message="Timeout waiting for __formSubmitted to be true."
        )
        form_submitted = self.driver.execute_script("return window.__formSubmitted;")
        self.assertTrue(form_submitted, "Form should have been submitted.")
        print("SUCCESS: Submit action on form verified.")

    # def test_submit_action_on_button_in_form(self):
    #     print("\n--- Running test_submit_action_on_button_in_form ---")
    #     self._inject_and_reset_test_harness()  # Inject and reset for this test
    #     WebDriverWait(self.driver, 5).until(
    #         EC.element_to_be_clickable((By.ID, "internalSubmitButton"))
    #     )
    #     plan = [{"action": "submit_form", "selector": "#internalSubmitButton"}]
    #     result = self._execute_plan_and_get_result(plan)
    #
    #     self.assertIsNotNone(result, "Result should not be None.")
    #     self.assertIn('results', result, "Result dictionary should contain 'results' key.")
    #     self.assertEqual(result["status"], "completed", "Plan status should be completed for submit action on button.")
    #     self.assertTrue(result["results"][0]["success"], "Submit form via button action should be successful.")
    #
    #     # Added sleep to allow browser to process the event and update the flag
    #     time.sleep(1)
    #
    #     # Explicitly wait for the flag to be set by the HTML's submit event listener
    #     WebDriverWait(self.driver, 5).until(
    #         lambda driver: driver.execute_script("return window.__formSubmitted2 === true;"),
    #         message="Timeout waiting for __formSubmitted2 to be true."
    #     )
    #     form_submitted = self.driver.execute_script("return window.__formSubmitted2;")
    #     self.assertTrue(form_submitted, "Form should have been submitted via button.")
    #     print("SUCCESS: Submit action on button in form verified.")

    def test_select_option_by_value(self):
        print("\n--- Running test_select_option_by_value ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        select_dropdown_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "selectDropdown"))
        )
        plan = [{"action": "select_option_by_value", "selector": "#selectDropdown", "value": "opt2"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for select_option.")
        self.assertTrue(result["results"][0]["success"], "Select option by value action should be successful.")

        # Directly assert on the select element's value
        WebDriverWait(self.driver, 5).until(
            lambda driver: select_dropdown_element.get_attribute('value') == "opt2",
            message="Timeout waiting for selectDropdown value to be 'opt2'."
        )
        selected_value = select_dropdown_element.get_attribute('value')
        self.assertEqual(selected_value, "opt2", "Option should be selected by value.")
        print("SUCCESS: Select option by value verified.")

    def test_select_option_by_index(self):
        print("\n--- Running test_select_option_by_index ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        select_dropdown_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "selectDropdown"))
        )
        plan = [{"action": "select_option_by_index", "selector": "#selectDropdown",
                 "index": 1}]  # Selects Option One (value="opt1")
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for select_option by index.")
        self.assertTrue(result["results"][0]["success"], "Select option by index action should be successful.")

        # Directly assert on the select element's value
        WebDriverWait(self.driver, 5).until(
            lambda driver: select_dropdown_element.get_attribute('value') == "opt1",
            message="Timeout waiting for selectDropdown value to be 'opt1'."
        )
        selected_value = select_dropdown_element.get_attribute('value')
        self.assertEqual(selected_value, "opt1", "Option should be selected by index.")
        print("SUCCESS: Select option by index verified.")

    def test_check_checkbox_action(self):
        print("\n--- Running test_check_checkbox_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        checkbox_input_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "checkboxInput"))
        )
        # Initial state: checked=true
        self.assertTrue(checkbox_input_element.is_selected(), "Checkbox should be checked initially.")

        # Test uncheck
        plan_uncheck = [{"action": "check_checkbox", "selector": "#checkboxInput", "checked": False}]
        result_uncheck = self._execute_plan_and_get_result(plan_uncheck)

        self.assertIsNotNone(result_uncheck, "Result should not be None for uncheck.")
        self.assertIn('results', result_uncheck, "Result dictionary should contain 'results' key for uncheck.")
        self.assertEqual(result_uncheck["status"], "completed", "Plan status should be completed for uncheck action.")
        self.assertTrue(result_uncheck["results"][0]["success"], "Uncheck checkbox action should be successful.")

        WebDriverWait(self.driver, 5).until(
            lambda driver: not checkbox_input_element.is_selected(),
            message="Timeout waiting for checkbox to be unchecked."
        )
        self.assertFalse(checkbox_input_element.is_selected(), "Checkbox should be unchecked.")

        # Test check
        plan_check = [{"action": "check_checkbox", "selector": "#checkboxInput", "checked": True}]
        result_check = self._execute_plan_and_get_result(plan_check)

        self.assertIsNotNone(result_check, "Result should not be None for check.")
        self.assertIn('results', result_check, "Result dictionary should contain 'results' key for check.")
        self.assertEqual(result_check["status"], "completed", "Plan status should be completed for check action.")
        self.assertTrue(result_check["results"][0]["success"], "Check checkbox action should be successful.")

        WebDriverWait(self.driver, 5).until(
            lambda driver: checkbox_input_element.is_selected(),
            message="Timeout waiting for checkbox to be checked."
        )
        self.assertTrue(checkbox_input_element.is_selected(), "Checkbox should be checked.")
        print("SUCCESS: Checkbox actions verified.")

    def test_check_radio_button_action(self):
        print("\n--- Running test_check_radio_button_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        radio1_element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "radio1")))
        radio2_element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "radio2")))

        # Initial state: radio2 is checked, radio1 is not
        self.assertFalse(radio1_element.is_selected(), "Radio button 1 should be unchecked initially.")
        self.assertTrue(radio2_element.is_selected(), "Radio button 2 should be checked initially.")

        # Check radio1
        plan = [{"action": "check_radio", "selector": "#radio1"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for check radio.")
        self.assertTrue(result["results"][0]["success"], "Check radio button action should be successful.")

        WebDriverWait(self.driver, 5).until(
            lambda driver: radio1_element.is_selected(),
            message="Timeout waiting for radio button 1 to be checked."
        )
        self.assertTrue(radio1_element.is_selected(), "Radio button 1 should be checked.")
        self.assertFalse(radio2_element.is_selected(), "Radio button 2 should be unchecked after radio 1 is checked.")
        print("SUCCESS: Radio button action verified.")

    def test_simulate_enter_action(self):
        print("\n--- Running test_simulate_enter_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        text_input_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "textInput"))
        )
        # Ensure focus for keypress events by clicking it first
        text_input_element.click()

        plan = [{"action": "simulate_enter", "selector": "#textInput"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for simulate_enter.")
        self.assertTrue(result["results"][0]["success"], "Simulate enter action should be successful.")

        # Explicitly wait for the flag to be set by the HTML's keypress listener
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script("return window.__enterPressed === true;"),
            message="Timeout waiting for __enterPressed to be true."
        )
        enter_pressed = self.driver.execute_script("return window.__enterPressed;")
        self.assertTrue(enter_pressed, "Enter keypress event should have been simulated.")
        print("SUCCESS: Simulate enter action verified.")

    def test_element_not_found(self):
        print("\n--- Running test_element_not_found ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        # This test intentionally looks for a non-existent element.
        plan = [{"action": "click", "selector": "#nonExistentElement"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "failed", "Plan status should be failed for element not found.")
        self.assertFalse(result["results"][0]["success"], "Action should fail if element not found.")
        self.assertIn("not found", result["results"][0]["error"], "Error message should indicate element not found.")
        print("SUCCESS: Element not found handled correctly.")

    def test_unknown_action(self):
        print("\n--- Running test_unknown_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        plan = [{"action": "unsupported_action", "selector": "#anyElement"}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "failed", "Plan status should be failed for unknown action.")
        self.assertFalse(result["results"][0]["success"], "Action should fail for unknown type.")
        self.assertIn("Unknown action type", result["results"][0]["error"],
                      "Error message should indicate unknown action.")
        print("SUCCESS: Unknown action handled correctly.")

    def test_sensitive_input_with_confirmation(self):
        print("\n--- Running test_sensitive_input_with_confirmation ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        password_input_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "passwordInput"))
        )
        self.driver.execute_script("window.__mockConfirmationResult = true;")  # Set mock result to true

        plan = [{"action": "enter_value", "element": "#passwordInput", "data": "mySecret", "is_sensitive": True}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan should complete if sensitive input confirmed.")
        self.assertTrue(result["results"][0]["success"], "Sensitive input action should be successful.")

        # Directly assert on the input field's value
        WebDriverWait(self.driver, 5).until(
            EC.text_to_be_present_in_element_value((By.ID, "passwordInput"), "mySecret"),
            message="Timeout waiting for passwordInput value to be 'mySecret'."
        )
        input_value = password_input_element.get_attribute('value')
        self.assertEqual(input_value, "mySecret", "Password input field value should be updated.")
        print("SUCCESS: Sensitive input with confirmation verified.")

    def test_sensitive_input_no_confirmation(self):
        print("\n--- Running test_sensitive_input_no_confirmation ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "passwordInput"))
        )
        self.driver.execute_script("window.__mockConfirmationResult = false;")  # Set mock result to false

        plan = [{"action": "enter_value", "element": "#passwordInput", "data": "mySecret", "is_sensitive": True}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "failed", "Plan should fail if sensitive input not confirmed.")
        self.assertFalse(result["results"][0]["success"], "Sensitive input action should fail.")
        self.assertIn("Confirmation denied", result["results"][0]["error"],
                      "Error message should indicate confirmation denial.")

        # Ensure the password input value remains empty
        password_value = self.driver.find_element(By.ID, "passwordInput").get_attribute('value')
        self.assertEqual(password_value, "", "Password input field value should NOT be updated.")
        print("SUCCESS: Sensitive input without confirmation verified.")

    def test_non_sensitive_from_user_input(self):
        print("\n--- Running test_non_sensitive_from_user_input ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        text_input_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "textInput"))
        )
        self.driver.execute_script("window.__mockConfirmationResult = 'User provided value';")  # Set mock result to a string

        plan = [{"action": "enter_value", "element": "#textInput", "from_user_input": True}]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan should complete for non-sensitive from_user input.")
        self.assertTrue(result["results"][0]["success"], "Non-sensitive user input action should be successful.")

        # Directly assert on the input field's value
        WebDriverWait(self.driver, 5).until(
            EC.text_to_be_present_in_element_value((By.ID, "textInput"), "User provided value"),
            message="Timeout waiting for textInput value to be 'User provided value'."
        )
        input_value = text_input_element.get_attribute('value')
        self.assertEqual(input_value, "User provided value", "User input should have been processed.")
        print("SUCCESS: Non-sensitive from_user input verified.")

    def test_multiple_actions_in_plan(self):
        print("\n--- Running test_multiple_actions_in_plan ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        text_input_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "textInput"))
        )
        click_button_element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "clickButton"))
        )

        plan = [
            {"action": "enter_value", "element": "#textInput", "data": "Multi-action test"},
            {"action": "click", "selector": "#clickButton"}
        ]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Plan status should be completed for multiple actions.")
        self.assertEqual(len(result["results"]), 2, "Should have results for two actions.")
        self.assertTrue(result["results"][0]["success"], "First action should be successful.")
        self.assertTrue(result["results"][1]["success"], "Second action should be successful.")

        # Verify first action (enter_value)
        WebDriverWait(self.driver, 5).until(
            EC.text_to_be_present_in_element_value((By.ID, "textInput"), "Multi-action test"),
            message="Timeout waiting for textInput value to be 'Multi-action test'."
        )
        input_value = text_input_element.get_attribute('value')
        self.assertEqual(input_value, "Multi-action test", "First action (type) failed.")

        # Verify second action (click)
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script("return window.__buttonClicked === true;"),
            message="Timeout waiting for __buttonClicked to be true after multiple actions."
        )
        button_clicked = self.driver.execute_script("return window.__buttonClicked;")
        self.assertTrue(button_clicked, "Second action (click) failed.")
        print("SUCCESS: Multiple actions in plan verified.")

    def test_plan_with_failing_action(self):
        print("\n--- Running test_plan_with_failing_action ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.ID, "textInput"))
        )
        plan = [
            {"action": "enter_value", "element": "#textInput", "data": "This will pass"},
            {"action": "click", "selector": "#nonExistentButton"}
        ]
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "failed", "Plan status should be failed if any action fails.")
        self.assertTrue(result["results"][0]["success"], "First action should still be successful.")
        self.assertFalse(result["results"][1]["success"], "Second action should fail.")
        self.assertIn("not found", result["results"][1]["error"], "Error message should indicate element not found.")

        # Verify first action's effect
        input_value = self.driver.find_element(By.ID, "textInput").get_attribute('value')
        self.assertEqual(input_value, "This will pass", "First action (type) should have succeeded.")
        print("SUCCESS: Plan with failing action verified.")

    def test_empty_plan(self):
        print("\n--- Running test_empty_plan ---")
        self._inject_and_reset_test_harness()  # Inject and reset for this test
        plan = []
        result = self._execute_plan_and_get_result(plan)

        self.assertIsNotNone(result, "Result should not be None.")
        self.assertIn('results', result, "Result dictionary should contain 'results' key.")
        self.assertEqual(result["status"], "completed", "Empty plan should complete successfully.")
        self.assertEqual(len(result["results"]), 0, "Should have no results for an empty plan.")
        print("SUCCESS: Empty plan verified.")

