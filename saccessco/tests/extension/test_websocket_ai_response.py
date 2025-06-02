# saccessco/tests/extension/test_websocket_ai_response.py
import time
import json
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from unittest.mock import AsyncMock, patch

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

# Correct WebSocket readyState constants
class WebSocket:
    OPEN = 1
    CLOSED = 3 # Corrected: WebSocket.CLOSED is 3, not 2

# Helper function to trigger AI response from backend
def trigger_ai_response_to_browser(conversation_id, ai_response_data):
    channel_layer = get_channel_layer()
    if channel_layer:
        # Ensure the group name matches what your consumer expects
        group_name = f"WEB_SOCKET_GROUP_NAME_{conversation_id}"
        print(f"Attempting to send AI response to group '{group_name}'")
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "ai_response",  # Matches the consumer's method name
                    "ai_response": ai_response_data    # The structured AI response
                }
            )
            print(f"Backend triggered AI response to group '{group_name}' with data: {ai_response_data}")
        except Exception as e:
            print(f"ERROR: Failed to send AI response to channel layer group: {e}")
    else:
        print("ERROR: Channel layer not available. Cannot send AI response.")


class WebSocketAIResponseTest(AbstractExtensionPageTest):
    def test_backend_ai_response_triggers_js_actions(self):
        # 1. Set a conversation_id for this test and initialize the JS array for received messages.
        test_conversation_id = "test_ai_response_conv"
        self.driver.execute_script(f"""
            window.conversation_id = '{test_conversation_id}';
            window.__receivedWebSocketMessages = []; // Initialize the array for testing
            console.log('Test setup: window.conversation_id set to {test_conversation_id}');
        """)

        # 2. Initialize WebSocket in the browser using the actual websocket.js code
        self.driver.execute_script("window.websocket.initializeAIWebSocket();")
        print("INFO: window.websocket.initializeAIWebSocket() called.")

        # 3. Wait for the WebSocket to connect by directly checking its readyState.
        # WebSocket.OPEN state is 1.
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return window.aiWebSocketReceiver && window.aiWebSocketReceiver.socket && window.aiWebSocketReceiver.socket.readyState === 1;")
            )
            print("INFO: WebSocket connection established (verified via readyState).")
        except TimeoutException:
            js_logs = self.driver.get_log('browser')
            print("\n--- BROWSER CONSOLE LOGS (from client-side during connection timeout) ---")
            for entry in js_logs:
                print(entry)
            print("-------------------------------------------------------------------------")
            self.fail("Timed out waiting for WebSocket to connect. Check browser logs above and WebSocket readyState.")

        # Give the WebSocket a *tiny* moment for any initial messages (like client_hello) to be sent,
        # though readyState is usually sufficient.
        time.sleep(0.1)

        # 4. Prepare the structured AI response payload
        ai_response_payload = {
            "speak": "Hello from the AI model!",
            "display": "AI says: Hello!", # Add a display message for chatModule
            "execute": [
                # Note: These selectors/actions might need to exist in your test_page_manipulator.html
                # For this test, we are primarily verifying the message receipt, not the DOM manipulation.
                {"action": "enter_value", "element": "#textInput", "data": "AI says hello"},
                {"action": "click", "element": "#clickButton"}
            ]
        }

        # 5. Call the helper function to trigger the backend message.
        trigger_ai_response_to_browser(test_conversation_id, ai_response_payload)
        print(f"INFO: Triggered backend AI response via helper function.")

        # 6. Wait for the WebSocket message to be received and stored in the __receivedWebSocketMessages array.
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return window.__receivedWebSocketMessages.length > 0;")
            )
            print("INFO: Raw WebSocket message received in browser (verified via JS array).")
        except TimeoutException:
            received_messages = self.driver.execute_script("return window.__receivedWebSocketMessages;")
            print(f"ERROR: Timeout waiting for RAW JS WebSocket message. Received messages in array: {received_messages}")
            self.fail("Timed out waiting for raw WebSocket message to be received in JS array.")

        # 7. Retrieve the messages directly from the JS array and assert their content.
        received_messages_js_array = self.driver.execute_script("return window.__receivedWebSocketMessages;")
        self.assertGreater(len(received_messages_js_array), 0, "No raw WebSocket messages were received in JS array.")

        try:
            # Get the last message from the array
            last_message_data = json.loads(received_messages_js_array[-1])
            self.assertEqual(last_message_data['speak'], ai_response_payload['speak'], "Incorrect 'speak' content in received message.")
            self.assertEqual(last_message_data['display'], ai_response_payload['display'], "Incorrect 'display' content in received message.")
            self.assertEqual(last_message_data['execute'], ai_response_payload['execute'], "Incorrect 'execute' content in received message.")
            print("SUCCESS: Raw WebSocket message content verified.")
        except json.JSONDecodeError as e:
            self.fail(f"Failed to parse received WebSocket message as JSON: {e}. Message: {received_messages_js_array[-1]}")
        except KeyError as e:
            self.fail(f"Missing key in received WebSocket message: {e}. Message: {last_message_data}")

        print("SUCCESS: AI response processing (raw message receipt) verified.")

        # Clean up: Close the WebSocket connection after the test
        # This calls the exposed disconnectAIWebSocket method.
        # Note: Your websocket.js doesn't have a `disconnectAIWebSocket` function directly on `window.websocket`.
        # It has `initializeAIWebSocket` which sets `window.aiWebSocketReceiver`.
        # So, the correct call is `window.aiWebSocketReceiver.close();`
        self.driver.execute_script("window.aiWebSocketReceiver.close();")
        print("INFO: window.aiWebSocketReceiver.close() called for cleanup.")

        # Optional: Wait for the closed message in logs for explicit confirmation
        try:
            # Look for the specific log message from WebSocketAIReceiver's close method
            WebDriverWait(self.driver, 5).until(
                lambda d: any("WebSocketAIReceiver: Closing connection intentionally." in entry['message'] for entry in d.get_log('browser'))
            )
            print("INFO: WebSocket connection confirmed closed via console log.")
        except TimeoutException:
            print("WARNING: Timed out waiting for WebSocket disconnect confirmation log.")

