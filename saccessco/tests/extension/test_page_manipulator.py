# saccessco/tests/extension/test_page_manipulator.py

import json
import time
from selenium.common.exceptions import WebDriverException
from django.urls import reverse

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest
from selenium.webdriver.support.ui import WebDriverWait # Import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC # Import expected_conditions


class PageManipulatorTest(AbstractExtensionPageTest):
    """
    Tests the page_manipulator.js module's ability to interact with DOM elements.
    """
    URL_NAME = 'test_page_manipulator'
    def setUp(self):
        super().setUp()
        self.driver.execute_script("""
                    window.chatModule = window.chatModule || {};

                    window.chatModule.askConfirmation = async (prompt) => {
                        console.log(`MOCK OVERRIDE: chatModule.askConfirmation called for: ${prompt}`);
                        if (prompt === "Proceed automatically?") {
                            // This prompt needs to return the 'proceed' or 'deny' confirmation
                            return Promise.resolve(window._testUserProceedConfirmation || 'proceed');
                        } else if (prompt === "Spell your input now:") {
                            // This prompt needs to return the *mocked spelled input*
                            return Promise.resolve(window._testUserSpelledInput || '');
                        } else if (prompt === "Enter the value:") {
                            // This prompt needs to return the *mocked direct input* for non-sensitive fields
                            return Promise.resolve(window._testUserDirectInput || '');
                        }
                        console.warn(`MOCK OVERRIDE: Unhandled chatModule.askConfirmation prompt: ${prompt}`);
                        return Promise.resolve('');
                    };

                    // Define distinct global variables for test control:
                    window._testUserProceedConfirmation = 'proceed'; // Default for the first prompt
                    window._testUserSpelledInput = ''; // Default for the "spell" prompt
                    window._testUserDirectInput = ''; // Default for non-sensitive "from_user" prompts

                    console.log('INFO: Specific chatModule.askConfirmation mock re-injected with prompt-aware logic.');
                """)

    # --- Helper methods to query DOM state from Python ---

    def _get_element_value(self, selector):
        """Returns the value of an input/textarea element."""
        return self.driver.execute_script(
            f"return document.querySelector('{selector}') ? document.querySelector('{selector}').value : null;")

    def _is_element_focused(self, selector):
        """Checks if a specific element is currently focused."""
        return self.driver.execute_script(f"return document.activeElement === document.querySelector('{selector}');")

    def _get_element_checked(self, selector):
        """Returns the checked state of a checkbox/radio button."""
        return self.driver.execute_script(
            f"return document.querySelector('{selector}') ? document.querySelector('{selector}').checked : null;")

    def _get_select_selected_value(self, selector):
        """Returns the selected value of a select dropdown."""
        return self.driver.execute_script(
            f"return document.querySelector('{selector}') ? document.querySelector('{selector}').value : null;")

    def _get_element_text(self, selector):
        """Returns the text content of an element."""
        return self.driver.execute_script(
            f"return document.querySelector('{selector}') ? document.querySelector('{selector}').textContent : null;")

    def _get_current_url(self):
        """Returns the current URL of the browser."""
        return self.driver.current_url

    # --- Tests for individual actions ---

    def test_focus_action(self):
        print("\n--- Running test_focus_action ---")
        selector = "#targetDiv"

        # Ensure element is not focused initially
        self.assertFalse(self._is_element_focused(selector), "Element should not be focused initially.")

        plan = [{"element": selector, "action": "focus", "data": None}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self._get_browser_console_logs()

        self.assertEqual(result["status"], "completed", "Plan status should be completed for focus action.")
        self.assertEqual(result["step_statuses"][0], "ok", "Focus action step status should be ok.")
        self.assertTrue(self._is_element_focused(selector), "Target div should be focused after action.")

        print("SUCCESS: Focus action verified.")

    def test_enter_value_action(self):
        print("\n--- Running test_enter_value_action ---")
        selector = "#textInput"
        test_data = "Hello World"

        # Ensure initial value is not the test data
        self.assertNotEqual(self._get_element_value(selector), test_data, "Initial value should not be the test data.")

        plan = [{"element": selector, "action": "enter_value", "data": test_data}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for enter_value action.")
        self.assertEqual(result["step_statuses"][0], "ok", "Enter_value action step status should be ok.")
        self.assertEqual(self._get_element_value(selector), test_data, "Input value should be updated.")
        print("SUCCESS: Enter_value action verified.")

    def test_click_action(self):
        print("\n--- Running test_click_action ---")
        selector = "#clickButton"

        # Set up a JS flag to detect click, as it doesn't change DOM visibly here
        self.driver.execute_script(
            "window._buttonClicked = false; document.querySelector('#clickButton').onclick = function() { window._buttonClicked = true; };")

        plan = [{"element": selector, "action": "click", "data": None}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for click action.")
        self.assertEqual(result["step_statuses"][0], "ok", "Click action step status should be ok.")

        button_clicked = self.driver.execute_script("return window._buttonClicked;")
        self.assertTrue(button_clicked, "Button should have been clicked.")
        print("SUCCESS: Click action verified.")

    def test_submit_action_on_form(self):
        print("\n--- Running test_submit_action_on_form ---")
        selector = "#testForm"
        initial_url = self._get_current_url()

        plan = [{"element": selector, "action": "submit", "data": None}]
        # Executing the plan and expecting a page navigation
        # Use WebDriverWait to wait for the URL to change
        try:
            result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)
            self.assertEqual(result["status"], "completed", "Plan status should be completed for submit action.")
            self.assertEqual(result["step_statuses"][0], "ok", "Submit action step status should be ok.")

            time.sleep(1)  # Wait 1 second before checking for URL change

            WebDriverWait(self.driver, 5).until(
                EC.url_changes(initial_url)
            )
            self._get_browser_console_logs()
            self.assertIn("form-submit-success", self._get_current_url(),
                          "Should navigate to form submission success page.")
            print("SUCCESS: Submit action on form verified (page navigation).")
        except WebDriverException as e:
            self._get_browser_console_logs()
            self.fail(f"WebDriverException during form submission: {e}. Current URL: {self._get_current_url()}")

    def test_submit_action_on_button_in_form(self):
        print("\n--- Running test_submit_action_on_button_in_form ---")
        selector = "#internalSubmitButton"
        initial_url = self._get_current_url()

        plan = [{"element": selector, "action": "submit", "data": None}]
        try:
            result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)
            self.assertEqual(result["status"], "completed",
                             "Plan status should be completed for submit action on button.")
            self.assertEqual(result["step_statuses"][0], "ok", "Submit action on button step status should be ok.")

            WebDriverWait(self.driver, 5).until(
                EC.url_changes(initial_url)
            )
            self.assertIn("form-submit-success", self._get_current_url(),
                          "Should navigate to form submission success page after button submit.")
            print("SUCCESS: Submit action on button in form verified.")
        except WebDriverException as e:
            self.fail(f"WebDriverException during button form submission: {e}. Current URL: {self._get_current_url()}")

    def test_select_option_by_value(self):
        print("\n--- Running test_select_option_by_value ---")
        selector = "#selectDropdown"
        test_data = "opt2"

        self.assertNotEqual(self._get_select_selected_value(selector), test_data,
                            "Initial selection should not be opt2.")

        plan = [{"element": selector, "action": "select_option", "data": test_data}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for select_option.")
        self.assertEqual(result["step_statuses"][0], "ok", "Select_option step status should be ok.")
        self.assertEqual(self._get_select_selected_value(selector), test_data, "Dropdown should have opt2 selected.")
        print("SUCCESS: Select_option by value verified.")

    def test_select_option_by_index(self):
        print("\n--- Running test_select_option_by_index ---")
        selector = "#selectDropdown"
        test_data = 2  # Index 2 corresponds to 'opt3'
        expected_value = "opt2"

        self.assertNotEqual(self._get_select_selected_value(selector), expected_value,
                            "Initial selection should not be opt3.")

        plan = [{"element": selector, "action": "select_option", "data": test_data}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for select_option by index.")
        self.assertEqual(result["step_statuses"][0], "ok", "Select_option by index step status should be ok.")
        self.assertEqual(self._get_select_selected_value(selector), expected_value,
                         "Dropdown should have opt3 selected by index.")
        print("SUCCESS: Select_option by index verified.")

    def test_check_checkbox_action(self):
        print("\n--- Running test_check_checkbox_action ---")
        selector = "#checkboxInput"
        self.driver.execute_script(f"document.querySelector('{selector}').checked = false;")  # Ensure it's unchecked
        self.assertFalse(self._get_element_checked(selector), "Checkbox should be unchecked initially.")

        plan = [{"element": selector, "action": "check", "data": True}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for check action (true).")
        self.assertEqual(result["step_statuses"][0], "ok", "Check action step status should be ok (true).")
        self.assertTrue(self._get_element_checked(selector), "Checkbox should be checked.")

        plan = [{"element": selector, "action": "check", "data": False}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)
        self.assertEqual(result["status"], "completed", "Plan status should be completed for check action (false).")
        self.assertEqual(result["step_statuses"][0], "ok", "Check action step status should be ok (false).")
        self.assertFalse(self._get_element_checked(selector), "Checkbox should be unchecked.")
        print("SUCCESS: Check checkbox action verified.")

    def test_check_radio_button_action(self):
        print("\n--- Running test_check_radio_button_action ---")
        selector_radio1 = "#radio1"
        selector_radio2 = "#radio2"
        self.assertTrue(self._get_element_checked(selector_radio2), "Radio2 should be checked initially.")
        self.assertFalse(self._get_element_checked(selector_radio1), "Radio1 should be unchecked initially.")

        plan = [{"element": selector_radio1, "action": "check", "data": True}]  # Check radio1
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for check radio (true).")
        self.assertEqual(result["step_statuses"][0], "ok", "Check radio step status should be ok (true).")
        self.assertTrue(self._get_element_checked(selector_radio1), "Radio1 should be checked.")
        self.assertFalse(self._get_element_checked(selector_radio2), "Radio2 should be unchecked (due to group).")
        print("SUCCESS: Check radio button action verified.")

    def test_simulate_enter_action(self):
        print("\n--- Running test_simulate_enter_action ---")
        selector = "#textInput"
        # We need a way to detect the "Enter" event.
        # Let's attach an event listener in JS and store a flag.
        self.driver.execute_script(f"""
            window._enterEventDispatched = false;
            document.querySelector('{selector}').addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') {{
                    window._enterEventDispatched = true;
                }}
            }});
        """)

        plan = [{"element": selector, "action": "simulate_enter", "data": None}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "completed", "Plan status should be completed for simulate_enter.")
        self.assertEqual(result["step_statuses"][0], "ok", "Simulate_enter step status should be ok.")

        enter_dispatched = self.driver.execute_script("return window._enterEventDispatched;")
        self.assertTrue(enter_dispatched, "Enter keydown event should have been dispatched.")
        print("SUCCESS: Simulate_enter action verified.")

    # --- Tests for error handling and specific logic ---

    def test_element_not_found(self):
        print("\n--- Running test_element_not_found ---")
        selector = "#nonExistentElement"
        plan = [{"element": selector, "action": "click", "data": None}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "failed", "Plan status should be failed for element not found.")
        self.assertEqual(result["step_statuses"][0], "error", "Step status should be error for element not found.")
        self.assertIn("Element not found", result["error_message"], "Error message should indicate element not found.")
        print("SUCCESS: Element not found error handling verified.")

    def test_unknown_action(self):
        print("\n--- Running test_unknown_action ---")
        selector = "#textInput"
        plan = [{"element": selector, "action": "unknown_action", "data": None}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self.assertEqual(result["status"], "failed", "Plan status should be failed for unknown action.")
        self.assertEqual(result["step_statuses"][0], "error", "Step status should be error for unknown action.")
        self.assertIn("Unknown action", result["error_message"], "Error message should indicate unknown action.")
        print("SUCCESS: Unknown action error handling verified.")

    def test_sensitive_input_no_confirmation(self):
        print("\n--- Running test_sensitive_input_no_confirmation ---")
        selector = "#passwordInput"
        from_user_placeholder = "<<from user>>"

        # Set mock confirmation to 'no' for this test.
        # This must match the variable name used in the JS mock for "Proceed automatically?"
        self.driver.execute_script("window._testUserProceedConfirmation = 'no';") # <--- FIX THIS LINE

        # window._testSensitiveInputResponse is an old, unused variable now.
        # It's better to remove it if not relevant to avoid confusion, or ensure it's not needed.
        # You've commented out its use in JS, so removing it from here is fine.
        # self.driver.execute_script("window._testSensitiveInputResponse = 'not used';")

        plan = [{"element": selector, "action": "enter_value", "data": from_user_placeholder}]
        result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

        self._get_browser_console_logs() # Make sure to call this to see the logs next time!

        self.assertEqual(result["status"], "failed", "Plan should fail if sensitive input not confirmed.")
        self.assertIn("User did not confirm sensitive input", result["error_message"],
                      "Error message should reflect lack of confirmation.")
        self.assertEqual(self._get_element_value(selector), "", "Sensitive input field should remain empty.")
        print("SUCCESS: Sensitive input without confirmation handled.")

    def test_sensitive_input_with_confirmation(self):
        print("\n--- Running test_sensitive_input_with_confirmation ---")
        selector = "#passwordInput"
        from_user_placeholder = "<<from user>>"

        # This is the FINAL expected value *after* the JavaScript processing (removing spaces)
        expected_sensitive_data_final = "MySeCr3t!"

        # This is the data that the MOCK 'user' will "spell" to the system.
        # It must contain spaces, and when spaces are removed, it should equal expected_sensitive_data_final.
        mock_spelled_input = "M y S e C r 3 t !" # e.g., 'M y S e C r 3 t !' becomes 'MySeCr3t!'

        # 1. Set the mock response for the first prompt: "Proceed automatically?"
        self.driver.execute_script("window._testUserProceedConfirmation = 'proceed';")

        # 2. Set the mock response for the second prompt: "Spell your input now:"
        # This is what page_manipulator.js will receive as 'finalData' before .replace
        self.driver.execute_script(f"window._testUserSpelledInput = '{mock_spelled_input}';")

        plan = [{"element": selector, "action": "enter_value", "data": from_user_placeholder}]
        try:
            result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

            self._get_browser_console_logs()

            self.assertEqual(result["status"], "completed", "Plan should complete if sensitive input confirmed.")
            self.assertEqual(result["step_statuses"][0], "ok", "Step status should be ok.")
            # Assert against the final, cleaned value
            self.assertEqual(self._get_element_value(selector), expected_sensitive_data_final,
                             "Sensitive input field should be filled with provided data.")
            print("SUCCESS: Sensitive input with confirmation handled.")

        except WebDriverException as e:
            self._get_browser_console_logs()
            self.fail(f"WebDriverException during test: {e}. Current URL: {self._get_current_url()}")

    # Add or modify test_non_sensitive_from_user_input for completeness with the new mock variables

    def test_non_sensitive_from_user_input(self):
        print("\n--- Running test_non_sensitive_from_user_input ---")
        selector = "#textInput"
        from_user_placeholder = "<<from user>>"
        expected_data = "NonSensitiveValue"

        # Set the mock response for the "Enter the value:" prompt for non-sensitive fields
        self.driver.execute_script(f"window._testUserDirectInput = '{expected_data}';")

        plan = [{"element": selector, "action": "enter_value", "data": from_user_placeholder}]
        try:
            result = self.driver.execute_script("return window.pageManipulatorModule.executePlan(arguments[0]);", plan)

            self._get_browser_console_logs()

            self.assertEqual(result["status"], "completed", "Plan should complete for non-sensitive from_user input.")
            self.assertEqual(result["step_statuses"][0], "ok", "Step status should be ok.")
            self.assertEqual(self._get_element_value(selector), expected_data,
                             "Input field should be filled with provided data.")
            print("SUCCESS: Non-sensitive from_user input handled.")

        except WebDriverException as e:
            self._get_browser_logs()
            self.fail(f"WebDriverException during test: {e}. Current URL: {self._get_current_url()}")