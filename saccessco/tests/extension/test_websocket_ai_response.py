
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

from saccessco.tests.extension.abstract_extension_page_test import AbstractExtensionPageTest

class WebSocket:
    OPEN = 1
    CLOSED = 3 # Added CLOSED state for clarity (WebSocket.CLOSED is 3)

# Helper function to trigger AI response from backend
def trigger_ai_response_to_browser(conversation_id, ai_response_data):
    channel_layer = get_channel_layer()
    if channel_layer:
        group_name = f"WEB_SOCKET_GROUP_NAME_{conversation_id}" # Use the correct group name prefix
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "ai_response",  # Matches the consumer's method name
                "ai_response": ai_response_data    # The structured AI response
            }
        )
        print(f"Backend triggered AI response to group '{group_name}' with data: {ai_response_data}")
    else:
        print("ERROR: Channel layer not available. Cannot send AI response.")


class WebSocketAIResponseTest(AbstractExtensionPageTest):

    def test_backend_ai_response_triggers_js_actions(self):
        # 1. Set a conversation_id for this test.
        # This needs to be available to websocket.js via window.conversation_id
        # and also passed to the backend trigger.
        test_conversation_id = "test_ai_response_conv"
        self.driver.execute_script(f"""
            window.conversation_id = '{test_conversation_id}';
            console.log('Test setup: window.conversation_id set to {test_conversation_id}');
        """)

        # 2. Initialize WebSocketAIReceiver using the actual websocket.js code
        self.driver.execute_script("window.websocket.initializeAIWebSocket();")
        print("INFO: window.websocket.initializeAIWebSocket() called.")

        # 3. Wait for the WebSocketAIReceiver to connect or close.
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("""
                    return window.aiWebSocketReceiver && window.aiWebSocketReceiver.socket &&
                           (window.aiWebSocketReceiver.socket.readyState === WebSocket.OPEN ||
                            window.aiWebSocketReceiver.socket.readyState === WebSocket.CLOSED);
                """)
            )

            current_ready_state = self.driver.execute_script("return window.aiWebSocketReceiver.socket.readyState;")

            if current_ready_state == WebSocket.OPEN: # WebSocket.OPEN is 1
                print("INFO: WebSocketAIReceiver connection established.")
            else: # If it's not OPEN, it must be CLOSED or N/A
                js_logs = self.driver.get_log('browser') # Get browser console logs
                print("\n--- BROWSER CONSOLE LOGS (from client-side during connection attempt) ---")
                for entry in js_logs:
                    print(entry)
                print("-------------------------------------------------------------------------")
                self.fail(f"WebSocketAIReceiver did not open. Current readyState: {current_ready_state}. Check browser logs above.")

        except TimeoutException:
            js_logs = self.driver.get_log('browser')
            print("\n--- BROWSER CONSOLE LOGS (from client-side during connection timeout) ---")
            for entry in js_logs:
                print(entry)
            print("-------------------------------------------------------------------------")
            self.fail("Timed out waiting for WebSocketAIReceiver to connect or close within 10 seconds.")

        # --- IMPORTANT: Add a short delay AFTER connection establishment, BEFORE message trigger ---
        # This gives the browser's WebSocket event loop time to settle.
        time.sleep(1)

        # 4. Prepare the structured AI response payload
        ai_response_payload = {
            "speak": "Hello from the AI model!",
            "execute": [
                {"action": "type", "selector": "#inputField", "value": "AI says hello"},
                {"action": "click", "selector": "#submitButton"}
            ]
        }
        # json_payload = json.dumps(ai_response_payload) # Not used directly for trigger

        # 5. Call the helper function to trigger the backend message.
        trigger_ai_response_to_browser(test_conversation_id, ai_response_payload)
        print(f"INFO: Triggered backend AI response via helper function.")

        # --- IMPORTANT: Add a significant delay AFTER triggering backend message ---
        # This is the most crucial delay for diagnosing if the message is delayed.
        print("INFO: Waiting 5 seconds for WebSocket message to be processed by browser...")
        time.sleep(5) # Give plenty of time for message to arrive and onMessage to fire

        # --- DEBUG: Capture browser console logs *after the 5-second delay* ---
        print("\n--- BROWSER CONSOLE LOGS (after 5-second backend trigger delay) ---")
        for entry in self.driver.get_log('browser'):
            print(entry)
        print("--------------------------------------------------------------")
        # --- END DEBUG ---

        # 6. Wait for a raw WebSocket message to be received in the browser
        try:
            WebDriverWait(self.driver, 10).until( # Still give 10 seconds for the wait condition
                lambda d: d.execute_script("""
                    console.log('WebDriverWait check: __receivedWebSocketMessages.length =', window.__receivedWebSocketMessages ? window.__receivedWebSocketMessages.length : 'undefined');
                    return window.__receivedWebSocketMessages && window.__receivedWebSocketMessages.length > 0;
                """)
            )
            print("INFO: Raw WebSocket message received in browser (via WebDriverWait).")
        except TimeoutException:
            received_messages = self.driver.execute_script("return window.__receivedWebSocketMessages;")
            print(f"ERROR: Timeout waiting for RAW JS WebSocket message. Received messages: {received_messages}")

            print("\n--- BROWSER CONSOLE LOGS (ON TIMEOUT for message receipt) ---")
            for entry in self.driver.get_log('browser'):
                print(entry)
            print("------------------------------------------")

            self.fail("Timed out waiting for raw WebSocket message to be received.")


        # 7. Assert the content of the received message (after successful receipt)
        received_messages = self.driver.execute_script("return window.__receivedWebSocketMessages;")
        self.assertGreater(len(received_messages), 0, "No raw WebSocket messages were received.")

        try:
            last_message_data = json.loads(received_messages[-1])
            self.assertEqual(last_message_data['speak'], ai_response_payload['speak'], "Incorrect 'speak' content in received message.")
            self.assertEqual(last_message_data['execute'], ai_response_payload['execute'], "Incorrect 'execute' content in received message.")
            print("SUCCESS: Raw WebSocket message content verified.")
        except json.JSONDecodeError as e:
            self.fail(f"Failed to parse received WebSocket message as JSON: {e}. Message: {received_messages[-1]}")
        except KeyError as e:
            self.fail(f"Missing key in received WebSocket message: {e}. Message: {last_message_data}")

        print("SUCCESS: AI response processing (raw message receipt) verified.")

        # Clean up: Close the WebSocket connection after the test (optional, but good practice)
        self.driver.execute_script("if (window.aiWebSocketReceiver && window.aiWebSocketReceiver.socket) window.aiWebSocketReceiver.close();")