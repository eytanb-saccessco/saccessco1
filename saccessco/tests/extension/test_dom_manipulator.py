# saccessco/tests/extension/test_dom_manipulator.py

import os
import json
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from django.conf import settings

# Import the base test class
from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

class DomManipulatorTest(AbstractExtensionPageTest):
    JS_FILES = AbstractExtensionPageTest.JS_FILES + [
        os.path.join(settings.BASE_DIR, 'static', 'js', 'chrome_extension', 'dom_manipulator.js'),
    ]

    def setUp(self):
        super().setUp()
        print("INFO: DomManipulatorTest setUp called. Enhancing mocks.")
        self.driver.execute_script("""
            // Enhance speechModule with askUserInput for ParameterManager
            window.speechModule = window.speechModule || {};
            window.speechModule.askUserInput = async function(message, sensitive = false) {
                console.log("MOCK: speechModule.askUserInput called with message: " + message + ", sensitive: " + sensitive);
                window.__mockUserInputPrompts = window.__mockUserInputPrompts || [];
                window.__mockUserInputPrompts.push({ message: message, sensitive: sensitive });

                // Also simulate adding a message to the chat module when prompted
                if (window.chatModule && typeof window.chatModule.addMessage === 'function') {
                    window.chatModule.addMessage("Saccessco", message); // Saccessco is asking the question
                }

                return new Promise(resolve => {
                    setTimeout(() => {
                        const input = window.__nextMockUserInput;
                        console.log("MOCK: speechModule.askUserInput resolving with: " + input);
                        resolve(input);
                        window.__nextMockUserInput = undefined; // Reset for next prompt
                    }, 50); // Simulate a slight delay for user interaction
                });
            };
            window.__mockUserInputPrompts = [];
            window.__nextMockUserInput = undefined;

            // Enhance chatModule.addMessage to capture messages for assertions
            window.chatModule = window.chatModule || {};
            window.chatModule.addMessage = function(sender, message) {
                console.log("MOCK: chatModule.addMessage called: [" + sender + "] " + message);
                window.__chatModuleMessages = window.__chatModuleMessages || [];
                window.__chatModuleMessages.push({ sender: sender, message: message });
            };
            window.__chatModuleMessages = [];

            console.log("INFO: Mocks enhanced for DomManipulatorTest.");
        """)
        time.sleep(0.1)

    def test_execute_dynamic_dom_script_with_existing_parameters(self):
        print("\n--- Running test_execute_dynamic_dom_script_with_existing_parameters ---")
        # Script code (body only, no function declaration or return)
        script_code = """
            const username = await params.get('username');
            const password = await params.get('password', 'Please enter your password:', true);

            const usernameField = document.getElementById('usernameInput');
            const passwordField = document.getElementById('passwordInput');
            const submitButton = document.getElementById('submitButton');

            if (usernameField) usernameField.value = username;
            if (passwordField) passwordField.value = password;
            if (submitButton) submitButton.click();

            window.__domManipulationResult = {
                usernameValue: usernameField ? usernameField.value : null,
                passwordValue: passwordField ? passwordField.value : null,
                submitClicked: !!submitButton
            };
            console.log("Dynamic script finished. Result:", window.__domManipulationResult);
        """
        parameters = { "username": "testuser", "password": "testpassword123" }
        self.driver.execute_script("""
            document.body.innerHTML += `<input type="text" id="usernameInput" value=""><input type="password" id="passwordInput" value=""><button id="submitButton">Submit</button>`;
            console.log("Test HTML elements injected.");
        """)
        self.driver.execute_script(f"""
            window.domManipulatorModule.executeDynamicDomScript(
                {json.dumps(script_code)},
                {json.dumps(parameters)}
            );
        """)
        try:
            dom_result = WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return window.__domManipulationResult;")
            )
            print(f"INFO: Retrieved DOM manipulation result: {dom_result}")
            self.assertEqual(dom_result['usernameValue'], "testuser", "Username field not set correctly.")
            self.assertEqual(dom_result['passwordValue'], "testpassword123", "Password field not set correctly.")
            self.assertTrue(dom_result['submitClicked'], "Submit button was not clicked.")
            print("SUCCESS: Dynamic DOM script executed with existing parameters correctly.")
        except TimeoutException:
            self._get_browser_console_logs()
            self.fail("Timed out waiting for dynamic DOM manipulation result.")
        except Exception as e:
            self._get_browser_console_logs()
            self.fail(f"Error during test_execute_dynamic_dom_script_with_existing_parameters: {e}")


    def test_execute_dynamic_dom_script_with_missing_parameters_prompting_user(self):
        print("\n--- Running test_execute_dynamic_dom_script_with_missing_parameters_prompting_user ---")
        # Script code (body only, no function declaration or return)
        script_code = """
            const username = await params.get('username');
            const password = await params.get('password', 'Please enter your password:', true);

            if (!username || !password) {
                window.__domManipulationResult = { aborted: true, reason: 'Missing input after prompt' };
                return;
            }

            const usernameField = document.getElementById('usernameInput');
            const passwordField = document.getElementById('passwordInput');
            const submitButton = document.getElementById('submitButton');

            if (usernameField) usernameField.value = username;
            if (passwordField) passwordField.value = password;
            if (submitButton) submitButton.click();

            window.__domManipulationResult = {
                usernameValue: usernameField ? usernameField.value : null,
                passwordValue: passwordField ? passwordField.value : null,
                submitClicked: !!submitButton
            };
            console.log("Dynamic script finished. Result:", window.__domManipulationResult);
        """
        parameters = { "username": "prompt_user_test", "password": None }
        self.driver.execute_script("""
            document.body.innerHTML += `<input type="text" id="usernameInput" value=""><input type="password" id="passwordInput" value=""><button id="submitButton">Submit</button>`;
            console.log("Test HTML elements injected.");
        """)
        mock_user_input = "prompted_secret"
        self.driver.execute_script(f"window.__nextMockUserInput = '{mock_user_input}';")
        self.driver.execute_script(f"""
            window.__domManipulationResult = null;
            window.domManipulatorModule.executeDynamicDomScript(
                {json.dumps(script_code)},
                {json.dumps(parameters)}
            );
        """)
        try:
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return window.__mockUserInputPrompts.length > 0;")
            )
            prompts_captured = self.driver.execute_script("return window.__mockUserInputPrompts;")
            print(f"INFO: Captured prompts: {prompts_captured}")
            self.assertEqual(len(prompts_captured), 1, "Expected one user input prompt.")
            self.assertIn("Please enter your password:", prompts_captured[0]['message'], "Prompt message incorrect.")
            self.assertTrue(prompts_captured[0]['sensitive'], "Password prompt should be marked sensitive.")

            dom_result = WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return window.__domManipulationResult;")
            )
            print(f"INFO: Retrieved DOM manipulation result after prompting: {dom_result}")
            self.assertEqual(dom_result['usernameValue'], "prompt_user_test", "Username field not set correctly.")
            self.assertEqual(dom_result['passwordValue'], mock_user_input, "Password field not set correctly from prompt.")
            self.assertTrue(dom_result['submitClicked'], "Submit button was not clicked.")
            print("SUCCESS: Dynamic DOM script executed with missing parameters, prompting user correctly.")
        except TimeoutException:
            self._get_browser_console_logs()
            self.fail("Timed out waiting for dynamic DOM manipulation result after prompting.")
        except Exception as e:
            self._get_browser_console_logs()
            self.fail(f"Error during test_execute_dynamic_dom_script_with_missing_parameters: {e}")


    def test_execute_dynamic_dom_script_user_cancels_prompt(self):
        print("\n--- Running test_execute_dynamic_dom_script_user_cancels_prompt ---")
        # Script code (body only, no function declaration or return)
        script_code = """
            const username = await params.get('username');
            const password = await params.get('password', 'Please enter your password:', true);

            if (!username || !password) {
                window.__domManipulationResult = { aborted: true, reason: 'Missing input after prompt' };
                return;
            }

            const usernameField = document.getElementById('usernameInput');
            const passwordField = document.getElementById('passwordInput');
            const submitButton = document.getElementById('submitButton');

            if (usernameField) usernameField.value = username;
            if (passwordField) passwordField.value = password;
            if (submitButton) submitButton.click();

            window.__domManipulationResult = {
                usernameValue: usernameField ? usernameField.value : null,
                passwordValue: passwordField ? passwordField.value : null,
                submitClicked: !!submitButton
            };
            console.log("Dynamic script finished. Result:", window.__domManipulationResult);
        """
        parameters = { "username": "cancel_test", "password": None }
        self.driver.execute_script("""
            document.body.innerHTML += `<input type="text" id="usernameInput" value=""><input type="password" id="passwordInput" value=""><button id="submitButton">Submit</button>`;
            console.log("Test HTML elements injected.");
        """)
        self.driver.execute_script(f"window.__nextMockUserInput = null;")
        self.driver.execute_script(f"""
            window.__domManipulationResult = null;
            window.__chatModuleMessages = [];
            window.domManipulatorModule.executeDynamicDomScript(
                {json.dumps(script_code)},
                {json.dumps(parameters)}
            );
        """)
        try:
            # Wait for the initial prompt message to appear
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return window.__chatModuleMessages.length > 0;")
            )
            # Wait for the *cancellation* message to appear (which is added AFTER the prompt resolves with null)
            WebDriverWait(self.driver, 5).until(
                lambda d: any("Input for 'password' was not provided or cancelled. Action may be incomplete." in msg['message'] for msg in d.execute_script("return window.__chatModuleMessages;"))
            )

            chat_messages = self.driver.execute_script("return window.__chatModuleMessages;")
            print(f"INFO: Chat messages after user cancellation test: {chat_messages}")
            # Ensure both the initial prompt AND the cancellation message are there
            self.assertGreaterEqual(len(chat_messages), 2, "Expected at least two chat messages (prompt and cancellation).")
            # This is the specific assertion for the cancellation message
            expected_cancellation_message = "Input for 'password' was not provided or cancelled. Action may be incomplete."
            warning_message_found = any(expected_cancellation_message in msg['message'] for msg in chat_messages)
            self.assertTrue(warning_message_found, f"Expected cancellation message '{expected_cancellation_message}' not found in chat logs.")

            # Now wait for the DOM manipulation result, which should indicate abortion
            dom_result = WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return window.__domManipulationResult;")
            )
            print(f"INFO: Retrieved DOM manipulation result: {dom_result}")
            self.assertTrue(dom_result['aborted'], "Script should have aborted due to user cancellation.")
            self.assertEqual(dom_result['reason'], 'Missing input after prompt', "Incorrect abort reason.")

            username_field = self.driver.find_element(By.ID, 'usernameInput')
            password_field = self.driver.find_element(By.ID, 'passwordInput')
            self.assertEqual(username_field.get_attribute('value'), "", "Username field should not have been set.")
            self.assertEqual(password_field.get_attribute('value'), "", "Password field should not have been set.")

            print("SUCCESS: Dynamic DOM script handles user cancellation correctly.")
        except TimeoutException:
            self._get_browser_console_logs()
            self.fail("Timed out waiting for dynamic DOM manipulation result or chat messages after user cancellation.")
        except Exception as e:
            self._get_browser_console_logs()
            self.fail(f"Error during test_execute_dynamic_dom_script_user_cancels_prompt: {e}")

    def test_execute_dynamic_dom_script_with_script_error(self):
        print("\n--- Running test_execute_dynamic_dom_script_with_script_error ---")
        # Script code (body only, no function declaration or return)
        script_code = """
            const problematicValue = null.someProp; // This line will cause a TypeError
            console.log("This line should not be reached:", problematicValue);
        """
        parameters = {}
        self.driver.execute_script(f"""
            window.__domManipulationResult = null;
            window.__chatModuleMessages = [];
            window.domManipulatorModule.executeDynamicDomScript(
                {json.dumps(script_code)},
                {json.dumps(parameters)}
            );
        """)
        try:
            WebDriverWait(self.driver, 5).until(
                # Check for the specific error message expected from the error handler in dom_manipulator.js
                lambda d: any("Error processing action: Cannot read properties of null (reading 'someProp')" in msg['message'] for msg in d.execute_script("return window.__chatModuleMessages;"))
            )
            chat_messages = self.driver.execute_script("return window.__chatModuleMessages;")
            print(f"INFO: Chat messages after error: {chat_messages}")
            error_message_found = any("Error processing action: Cannot read properties of null (reading 'someProp')" in msg['message'] for msg in chat_messages)
            self.assertTrue(error_message_found, "Expected an error message in chat module about script execution failure.")
            print("SUCCESS: Dynamic DOM script correctly reports script errors to chat module.")
        except TimeoutException:
            self._get_browser_console_logs()
            self.fail("Timed out waiting for error message in chat module.")
        except Exception as e:
            self._get_browser_console_logs()
            self.fail(f"Error during test_execute_dynamic_dom_script_with_script_error: {e}")
