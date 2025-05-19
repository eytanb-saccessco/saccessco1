# your_app_name/tests/test_channels.py
# Replace 'your_app_name' with the actual name of your Django app
# Make sure this file is located within your app's 'tests' directory

import json
import asynctest # Requires 'pip install asynctest'
from channels.testing import WebsocketCommunicator
from django.test import TestCase # Using Django's TestCase for settings/database context

# Import the function to get the channel layer
from channels.layers import get_channel_layer
import asyncio # Needed for asyncio.wait_for

# Import your consumer and the fixed group name
# Adjust import paths as necessary
from saccessco.consumers import AiConsumer, WEB_SOCKET_GROUP_NAME
from saccessco.tasks import AiResponse

# You MUST configure your CHANNEL_LAYERS in settings.py
# for this test to run correctly. The InMemoryChannelLayer is sufficient for testing.
# Example in settings.py:
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer"
#     }
# }


class AiConsumerChannelTests(TestCase, asynctest.TestCase):
    """
    Unit tests for the AiConsumer's interaction with the Channel Layer.
    Tests that messages sent to the group are received and sent back
    through the WebSocket.
    """

    # The asynctest.TestCase provides the necessary async test runner.
    # Inheriting from Django's TestCase provides Django settings/DB context if needed.

    async def test_ai_response_message_received_and_sent(self):
        """
        Test that a message sent to the consumer's group via the channel layer
        is correctly processed by ai_response_message and sent back via WebSocket.
        """
        # 1. Instantiate the consumer communicator
        # The communicator simulates a client connecting to the consumer.
        # Pass the ASGI application callable (result of .as_asgi()) and the path.
        # Since your consumer uses a fixed group name and doesn't get ID from URL,
        # the path here doesn't strictly matter for group joining, but it's required.
        # If your consumer *did* get an ID from the URL, the path would need to match routing.
        application = AiConsumer.as_asgi() # Explicitly get the ASGI application callable
        communicator = WebsocketCommunicator(application, "/ws/ai/") # Use a dummy path matching potential routing

        # 2. Connect the communicator
        # This runs the consumer's connect() method.
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # 3. Get the channel layer instance from the test environment
        # Use get_channel_layer() to access the test channel layer
        channel_layer = get_channel_layer()
        self.assertIsNotNone(channel_layer, "Channel layer should be available in the test environment.")
        # Remove await channel_layer.ready() - InMemoryChannelLayer does not have this method.


        # 4. Simulate a message being sent to the consumer's group via the channel layer
        # This mimics your tasks.py sending a message using channel_layer.group_send().
        # The message dictionary structure must match what the consumer's method expects.
        # Your task sends {'type': 'ai_response_message', 'message': ai_response}
        # Your consumer method is async def ai_response_message(self, message):
        # So the channel layer message sent *to the group* should be:
        test_ai_response_content = "Hello from the mock AI!"

        # Send the message to the group. The channel layer will route it to the connected consumer(s).
        await channel_layer.group_send(
            WEB_SOCKET_GROUP_NAME, # The fixed group name from your consumers.py
            AiResponse(test_ai_response_content).json
        )

        # 5. Receive the message sent *by the consumer* back through the WebSocket
        # The consumer's ai_response_message method should send a message using self.send().
        # We expect the consumer to send: json.dumps({'type': 'ai_response', 'message': message})
        # Use a timeout to prevent the test from hanging indefinitely if no message is received.
        try:
            response_from_consumer = await asyncio.wait_for(communicator.receive_from(), timeout=1.0) # Add timeout
        except asyncio.TimeoutError:
            self.fail("Timeout waiting for message from consumer over WebSocket.")


        # 6. Assert that the received message from the consumer is correct
        # The received data is a string, so parse it as JSON.
        received_data = json.loads(response_from_consumer)

        # Define the expected message structure that the consumer should send
        expected_message_from_consumer = [AiResponse(test_ai_response_content).json]

        # Assert that the entire received dictionary matches the expected structure
        self.assertEqual(received_data, expected_message_from_consumer)


        # 7. Disconnect the communicator
        await communicator.disconnect()

    # You could add more tests here, e.g.:
    # - Test disconnect handling
    # - Test receiving a message directly via WebSocket (if your consumer has a receive method)
    # - Test error handling in the consumer's ai_response_message method

