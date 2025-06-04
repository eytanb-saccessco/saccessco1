# saccessco/tests/extension/test_chat_module.py
import time
import json
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest


class ChatModuleTest(AbstractExtensionPageTest):
    chat_container_id = 'saccessco-chat-container'
    chat_input_id = 'saccessco-chat-input'
    chat_button_id = 'saccessco-chat-button'
    mic_button_id = 'saccessco-mic-button'
    chat_messages_id = 'saccessco-chat-messages'

    def setUp(self):
        super().setUp()
        # Ensure the chat module is initialized and visible for testing
        self.driver.execute_script("window.chatModule.initializeChatArea();")
        self.driver.execute_script(f"document.getElementById('{self.chat_container_id}').style.display = 'block';")

        # Inject mock speechModule for chat_module.js to interact with
        self.driver.execute_script("""
            window.speechModule = {
                startListening: async function() {
                    // This mock simulates speech recognition.
                    // It will return a promise that resolves with a predefined transcript.
                    // We'll use a global variable to control the mock's return value.
                    console.log("Mocked speechModule.startListening called.");
                    return new Promise(resolve => {
                        setTimeout(() => {
                            const transcript = window.__mockSpeechTranscript || "Mocked speech input.";
                            console.log("Mocked speechModule.startListening resolving with:", transcript);
                            resolve(transcript);
                        }, 50); // Simulate a very short delay for listening
                    });
                },
                stopListening: function() {
                    console.log("Mock speechModule.stopListening called.");
                    // In a real scenario, this would stop active recognition.
                }
            };
            console.log("Mock window.speechModule injected for chat_module.js tests.");
        """)
        # Give a moment for the elements to render
        time.sleep(0.1)

    def test_chat_ui_elements_exist(self):
        print("INFO: test_chat_ui_elements_exist")
        # Verify chat container exists
        chat_container = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, self.chat_container_id))
        )
        self.assertIsNotNone(chat_container)
        self.assertTrue(chat_container.is_displayed())

        # Verify chat input exists
        chat_input = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, self.chat_input_id))
        )
        self.assertIsNotNone(chat_input)

        # Verify chat button exists
        chat_button = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, self.chat_button_id))
        )
        self.assertIsNotNone(chat_button)
        self.assertEqual(chat_button.text, 'Send')

        # Verify microphone button exists (NEW)
        mic_button = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.ID, self.mic_button_id))
        )
        self.assertIsNotNone(mic_button)
        self.assertIn('🎤', mic_button.text)  # Check for microphone icon
        print("SUCCESS: Chat UI elements exist.")

    def test_add_message_displays_text(self):
        print("INFO: test_add_message_displays_text")
        message_to_add = "Hello, world!"
        self.driver.execute_script(f"window.chatModule.addMessage('TestSender', '{message_to_add}');")

        # Wait for the message to appear in the messages div
        message_div_xpath = f"//div[@id='{self.chat_messages_id}']/div[contains(text(), 'TestSender: {message_to_add}')]"
        added_message_element = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, message_div_xpath))
        )
        self.assertIsNotNone(added_message_element)
        self.assertTrue(added_message_element.is_displayed())
        self.assertIn(f"TestSender: {message_to_add}", added_message_element.text)
        print("SUCCESS: addMessage displays text correctly.")

    def test_user_input_clears_and_dispatches_event(self):
        print("INFO: test_user_input_clears_and_dispatches_event")
        user_message = "This is a user test message."

        # Inject an event listener into the browser context
        self.driver.execute_script("""
            window.__lastUserPromptEvent = null;
            document.addEventListener('saccessco:userPromptSubmitted', function(e) {
                window.__lastUserPromptEvent = e.detail.prompt;
            });
        """)

        # Find input and send button
        chat_input = self.driver.find_element(By.ID, self.chat_input_id)
        send_button = self.driver.find_element(By.ID, self.chat_button_id)

        # Type message and click send
        chat_input.send_keys(user_message)
        send_button.click()

        # Verify input is cleared
        self.assertEqual(chat_input.get_attribute('value'), '', "Input was not cleared after sending.")

        # Verify message is displayed
        user_message_xpath = f"//div[@id='{self.chat_messages_id}']/div[contains(text(), 'User: {user_message}')]"
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, user_message_xpath))
        )

        # Verify event was dispatched and captured
        dispatched_prompt = WebDriverWait(self.driver, 5).until(
            lambda d: d.execute_script("return window.__lastUserPromptEvent;")
        )
        self.assertEqual(dispatched_prompt, user_message,
                         "saccessco:userPromptSubmitted event not dispatched correctly.")
        print("SUCCESS: User input clears and dispatches event.")

    def test_ask_confirmation_flow(self):
        print("INFO: test_ask_confirmation_flow")
        prompt_text = "Are you sure?"

        # Inject event listener for confirmation resolution
        self.driver.execute_script("""
            window.__lastConfirmationEvent = null;
            document.addEventListener('saccessco:confirmationResolved', function(e) {
                window.__lastConfirmationEvent = {
                    userMessage: e.detail.userMessage,
                    isConfirmed: e.detail.isConfirmed
                };
            });
        """)

        # Call askConfirmation and keep the promise in a global variable for later resolution check
        self.driver.execute_script(f"""
            window.__confirmationPromise = window.chatModule.askConfirmation('{prompt_text}');
        """)

        # Verify confirmation prompt is displayed in chat
        confirmation_message_xpath = f"//div[@id='{self.chat_messages_id}']/div[contains(text(), \"Saccessco: {prompt_text}\")]"
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, confirmation_message_xpath))
        )
        print("INFO: Confirmation prompt displayed.")

        # Simulate user typing 'yes'
        chat_input = self.driver.find_element(By.ID, self.chat_input_id)
        send_button = self.driver.find_element(By.ID, self.chat_button_id)
        chat_input.send_keys("yes")
        send_button.click()

        # Verify input is cleared
        self.assertEqual(chat_input.get_attribute('value'), '', "Input was not cleared after confirmation response.")

        # Verify that the promise resolves to true and the event is dispatched
        confirmation_result = WebDriverWait(self.driver, 5).until(
            lambda d: d.execute_script("return window.__lastConfirmationEvent;"),
            message="Confirmation promise not resolved or event not dispatched."
        )

        self.assertIsNotNone(confirmation_result)
        self.assertTrue(confirmation_result['isConfirmed'], "Confirmation result was not true.")
        self.assertEqual(confirmation_result['userMessage'], "yes", "User message in confirmation event incorrect.")
        print("SUCCESS: askConfirmation flow handles 'yes' correctly.")

        # Test with 'no'
        self.driver.execute_script(f"""
            window.__confirmationPromise = window.chatModule.askConfirmation('Are you really sure?');
            window.__lastConfirmationEvent = null; // Reset for next check
        """)
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH,
                                            "//div[@id='saccessco-chat-messages']/div[contains(text(), \"Saccessco: Are you really sure?\")]"))
        )
        chat_input.send_keys("no")
        send_button.click()

        confirmation_result = WebDriverWait(self.driver, 5).until(
            lambda d: d.execute_script("return window.__lastConfirmationEvent;"),
            message="Second confirmation promise not resolved or event not dispatched."
        )
        self.assertIsNotNone(confirmation_result)
        self.assertFalse(confirmation_result['isConfirmed'], "Confirmation result was not false.")
        self.assertEqual(confirmation_result['userMessage'], "no",
                         "User message in second confirmation event incorrect.")
        print("SUCCESS: askConfirmation flow handles 'no' correctly.")

    def test_microphone_button_initiates_speech_input(self):
        print("INFO: test_microphone_button_initiates_speech_input")
        mic_button = self.driver.find_element(By.ID, self.mic_button_id)
        chat_input = self.driver.find_element(By.ID, self.chat_input_id)
        send_button = self.driver.find_element(By.ID, self.chat_button_id)

        # Set a specific transcript for the mock
        mock_transcript = "Hello Gemini, how are you?"
        self.driver.execute_script(f"window.__mockSpeechTranscript = '{mock_transcript}';")

        # Inject an event listener for user prompt
        self.driver.execute_script("""
            window.__lastUserPromptEvent = null;
            document.addEventListener('saccessco:userPromptSubmitted', function(e) {
                window.__lastUserPromptEvent = e.detail.prompt;
            });
        """)

        # Click the microphone button
        mic_button.click()

        # Wait for listening state (button appearance changes)
        WebDriverWait(self.driver, 5).until(
            lambda driver: mic_button.text == '🔴'
        )
        print("INFO: Mic button text changed to '🔴'")

        # Assert that input and send button are disabled while listening
        self.assertTrue(chat_input.get_attribute('disabled'), "Chat input should be disabled while listening.")
        self.assertTrue(send_button.get_attribute('disabled'), "Send button should be disabled while listening.")
        print("INFO: Input and send button are disabled while listening.")

        # Wait for the userPromptSubmitted event to be dispatched with the correct transcript
        dispatched_prompt = WebDriverWait(self.driver, 5).until(
            lambda d: d.execute_script("return window.__lastUserPromptEvent;")
        )
        self.assertEqual(dispatched_prompt, mock_transcript,
                         "saccessco:userPromptSubmitted event not dispatched with correct transcript.")
        print("INFO: saccessco:userPromptSubmitted event dispatched with correct transcript.")

        # Verify button appearance returned to normal and elements are re-enabled
        WebDriverWait(self.driver, 5).until(
            lambda driver: mic_button.text == '🎤'
        )
        print("INFO: Mic button text changed back to '🎤'")
        self.assertFalse(chat_input.get_attribute('disabled'), "Chat input should be re-enabled after listening.")
        self.assertFalse(send_button.get_attribute('disabled'), "Send button should be re-enabled after listening.")
        print("INFO: Input and send button are re-enabled after listening.")

        # Verify input was cleared by handleUserInput
        self.assertEqual(chat_input.get_attribute('value'), '', "Input was not cleared after speech input.")
        print("SUCCESS: Microphone button initiates speech input and processes it.")

    def test_chat_container_drag(self):
        print("INFO: test_chat_container_drag")
        chat_container = self.driver.find_element(By.ID, self.chat_container_id)
        initial_x = chat_container.location['x']
        initial_y = chat_container.location['y']

        # Simulate dragging
        action = ActionChains(self.driver)
        action.move_to_element(chat_container).click_and_hold().move_by_offset(50, 50).release().perform()

        time.sleep(0.5)  # Give time for repositioning

        final_x = chat_container.location['x']
        final_y = chat_container.location['y']

        # Assert that the position has changed
        self.assertNotEqual(initial_x, final_x)
        self.assertNotEqual(initial_y, final_y)
        print("SUCCESS: Chat container can be dragged.")

    def test_chat_container_resize(self):
        print("INFO: test_chat_container_resize")
        resize_handle = self.driver.find_element(By.ID, 'saccessco-chat-resize-handle')
        chat_container = self.driver.find_element(By.ID, self.chat_container_id)

        initial_width = chat_container.size['width']
        initial_height = chat_container.size['height']

        # Simulate resizing
        action = ActionChains(self.driver)
        action.move_to_element(resize_handle).click_and_hold().move_by_offset(50, 50).release().perform()

        time.sleep(0.5)  # Give time for resizing

        final_width = chat_container.size['width']
        final_height = chat_container.size['height']

        # Assert that the size has changed and is greater than initial
        self.assertGreater(final_width, initial_width)
        self.assertGreater(final_height, initial_height)

        # Assert that size doesn't go below minimum (approximate check)
        self.assertGreaterEqual(final_width, 150)
        self.assertGreaterEqual(final_height, 100)
        print("SUCCESS: Chat container can be resized.")
