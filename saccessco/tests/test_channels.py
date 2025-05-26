# your_app_name/tests/test_channels.py

import json
import asyncio
import sys # ADD THIS IMPORT
import channels # ADD THIS IMPORT
import asgiref # ADD THIS IMPORT

from django.test import TestCase
from unittest import IsolatedAsyncioTestCase

from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from channels.routing import ProtocolTypeRouter, URLRouter

from saccessco.consumers import AiConsumer
from saccessco.routing import websocket_urlpatterns

# Make sure your CHANNEL_LAYERS are configured in settings.py:
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer"
#     }
# }


class AiConsumerChannelTests(TestCase, IsolatedAsyncioTestCase):
    """
    Unit tests for the AiConsumer's interaction with the Channel Layer.
    Tests that messages sent to the group are received and sent back
    through the WebSocket.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # cls.user = User.objects.create_user(username='testuser', password='password')

        # Use your actual websocket_urlpatterns here
        cls.application = ProtocolTypeRouter({
            "websocket": URLRouter(websocket_urlpatterns),
        })

    async def test_ai_response_message_received_and_sent(self):
        """
        Test that a message sent to the consumer's group via the channel layer
        is correctly processed by ai_response and sent back via WebSocket.
        """
        # --- DIAGNOSTIC PRINTS START ---
        print("\n--- DEBUGGING PACKAGE PATHS ---")
        print(f"sys.version: {sys.version}")
        print(f"sys.executable: {sys.executable}")
        print(f"sys.path (important for module loading order):")
        for p in sys.path:
            print(f"  - {p}")
        print(f"channels.__version__: {channels.__version__} from {channels.__file__}")
        print(f"asgiref.__version__: {asgiref.__version__} from {asgiref.__file__}")
        print("--- DEBUGGING PACKAGE PATHS END ---\n")
        # --- DIAGNOSTIC PRINTS END ---

        # Define a test conversation ID and the corresponding group name
        test_conversation_id = "test_conv_123"
        test_conversation_group_name = f"{AiConsumer.GROUP_NAME_PREFIX}{test_conversation_id}"

        # 1. Prepare the scope_extension to mimic URL routing kwargs

        # 2. Instantiate the consumer communicator, passing the scope_extension
        # application = AiConsumer.as_asgi()

        communicator = WebsocketCommunicator(
            self.application,
            f"/ws/saccessco/ai/{test_conversation_id}/"
        )

        # 3. Connect the communicator
        connected, sub_protocol = await communicator.connect()
        self.assertTrue(connected)

        # 4. Get the channel layer instance
        channel_layer = get_channel_layer()
        self.assertIsNotNone(channel_layer, "Channel layer should be available in the test environment.")

        # 5. Define the structured AI response payload
        mock_ai_response_payload = {
            "type": "ai_text_response",
            "text": "This is a mock AI response for testing.",
            "sentiment": "positive"
        }

        # 6. Simulate a message being sent to the consumer's group via the channel layer
        await channel_layer.group_send(
            test_conversation_group_name,
            {
                'type': 'ai_response',
                'ai_response': mock_ai_response_payload,
            }
        )

        # 7. Receive the message sent by the consumer back through the WebSocket
        try:
            response_from_consumer_str = await asyncio.wait_for(communicator.receive_from(), timeout=1.0)
        except asyncio.TimeoutError:
            self.fail("Timeout waiting for message from consumer over WebSocket.")

        # 8. Assert that the received message from the consumer is correct
        received_data = json.loads(response_from_consumer_str)
        self.assertEqual(received_data, mock_ai_response_payload)

        # 9. Disconnect the communicator
        await communicator.disconnect()