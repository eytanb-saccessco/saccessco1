# saccessco/tests/extension/test_backend_communication.py

import json
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from django.urls import reverse
from django.conf import settings  # Import settings to access BASE_DIR

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

# Define the path to the backend_communicator.js module


class BackendCommunicationTest(AbstractExtensionPageTest):
    """
    Tests the communication from the frontend's backend_communicator.js
    to the Django backend API views using Selenium.
    """

    def test_send_user_prompt_success(self):
        """
        Tests sending a valid user prompt and expects a success response.
        """
        print("\n--- Running test_send_user_prompt_success ---")
        user_prompt_text = "What is the capital of France?"

        # Execute the JavaScript function and get its return value (the Promise result)
        # Selenium's execute_script can await Promises and return their resolved value.
        js_code = f"""
            return window.backendCommunicatorModule.sendUserPrompt('{user_prompt_text}');
        """
        print(f"INFO: Calling sendUserPrompt with: '{user_prompt_text}'")

        # The result will be the JSON response from the backend API
        response_data = self.driver.execute_script(js_code)

        print(f"INFO: Received response for user prompt: {response_data}")

        # Assert the expected response from the backend
        self.assertIsNotNone(response_data, "Response data should not be None.")
        self.assertIsInstance(response_data, dict, "Response data should be a dictionary (parsed JSON).")
        self.assertIn("message", response_data)
        self.assertIn("status", response_data)
        self.assertEqual(response_data["message"], "User prompt received successfully")
        self.assertEqual(response_data["status"], "success")

        print("SUCCESS: sendUserPrompt communication verified.")

    def test_send_page_change_success(self):
        """
        Tests sending valid page change HTML and expects a success response.
        """
        print("\n--- Running test_send_page_change_success ---")
        page_html_content = "<html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>"

        # Execute the JavaScript function and get its return value (the Promise result)
        js_code = f"""
            return window.backendCommunicatorModule.sendPageChange(`{page_html_content}`);
        """
        print(f"INFO: Calling sendPageChange with HTML length: {len(page_html_content)}")

        # The result will be the JSON response from the backend API
        response_data = self.driver.execute_script(js_code)

        print(f"INFO: Received response for page change: {response_data}")

        # Assert the expected response from the backend
        self.assertIsNotNone(response_data, "Response data should not be None.")
        self.assertIsInstance(response_data, dict, "Response data should be a dictionary (parsed JSON).")
        self.assertIn("message", response_data)
        self.assertIn("status", response_data)
        self.assertEqual(response_data["message"], "Page change received successfully")
        self.assertEqual(response_data["status"], "success")

        print("SUCCESS: sendPageChange communication verified.")

    def test_send_user_prompt_invalid_data(self):
        """
        Tests sending an invalid user prompt (empty text) and expects a 400 Bad Request.
        """
        print("\n--- Running test_send_user_prompt_invalid_data ---")
        invalid_prompt_text = ""  # UserPromptSerializer expects a non-empty prompt

        js_code = f"""
            return window.backendCommunicatorModule.sendUserPrompt('{invalid_prompt_text}');
        """
        print(f"INFO: Calling sendUserPrompt with invalid data: '{invalid_prompt_text}'")

        response_data = self.driver.execute_script(js_code)

        print(f"INFO: Received response for invalid user prompt: {response_data}")

        # Assert the expected error response from the backend (status 400)
        self.assertIsNotNone(response_data, "Response data should not be None.")
        self.assertIsInstance(response_data, dict, "Response data should be a dictionary (parsed JSON).")
        self.assertIn("prompt", response_data)  # Expecting validation error for 'prompt' field
        self.assertIn("This field may not be blank.", response_data["prompt"])

        print("SUCCESS: sendUserPrompt invalid data handling verified.")

    def test_send_page_change_invalid_data(self):
        """
        Tests sending invalid page change data (empty HTML) and expects a 400 Bad Request.
        """
        print("\n--- Running test_send_page_change_invalid_data ---")
        invalid_html_content = ""  # PageChangeSerializer expects a non-empty html

        js_code = f"""
            return window.backendCommunicatorModule.sendPageChange(`{invalid_html_content}`);
        """
        print(f"INFO: Calling sendPageChange with invalid HTML length: {len(invalid_html_content)}")

        response_data = self.driver.execute_script(js_code)

        print(f"INFO: Received response for invalid page change: {response_data}")

        # Assert the expected error response from the backend (status 400)
        self.assertIsNotNone(response_data, "Response data should not be None.")
        self.assertIsInstance(response_data, dict, "Response data should be a dictionary (parsed JSON).")
        self.assertIn("html", response_data)  # Expecting validation error for 'html' field
        self.assertIn("This field may not be blank.", response_data["html"])

        print("SUCCESS: sendPageChange invalid data handling verified.")

