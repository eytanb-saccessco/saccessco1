# saccessco/tests/test_conversation.py

import json
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import time
import logging
from concurrent.futures import ThreadPoolExecutor

# Import the Conversation class and its dependencies
from saccessco.conversation import Conversation
from saccessco.ai import User, Model
from saccessco.consumers import AiConsumer

# Import async_to_sync for patching
from asgiref.sync import async_to_sync # <--- ENSURE THIS IS IMPORTED

# Configure logging to see test output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("saccessco")  # Use the same logger name as in Conversation class

# --- Mocking Django Channels for standalone tests ---
# In a real Django project, settings are configured.
# For these unit tests, we need a minimal setup if not running via manage.py test
import os
from django.conf import settings
from channels.layers import InMemoryChannelLayer  # A test-friendly channel layer

if not settings.configured:
    settings.configure(
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer"
            }
        },
        SECRET_KEY='a-very-secret-key-for-testing-purposes',
        # Add any other minimal settings your AIEngine or other parts might require
        # For example, if AIEngine needs specific API keys from settings:
        # GEMINI_API_KEY='dummy_api_key_for_test',
    )
    import django

    django.setup()


# --- End Mocking Django Channels ---


class TestConversation(unittest.TestCase):

    # This method runs once before all tests in the class
    @classmethod
    def setUpClass(cls):
        # Clear any existing Conversation instances before tests run
        # This is important because of the __new__ instance management
        Conversation._instances = {}
        # Ensure the lock is re-initialized if needed, though usually not strictly necessary
        # if _instances is cleared.

    def setUp(self):
        # Reset instances for each test to ensure isolation, if not using setUpClass for full clear
        # For this specific __new__ pattern, setUpClass is more appropriate for clearing
        # if you want to ensure a clean slate for all tests.
        # If you want each test to start fresh, you'd move Conversation._instances = {} here.
        # For now, setUpClass handles it.
        pass

    def tearDown(self):
        # Shut down the executor for each Conversation instance created in a test
        # This prevents threads from lingering across tests
        for instance_id, instance in list(Conversation._instances.items()):
            if hasattr(instance, 'executor') and not instance.executor._shutdown:
                instance.shutdown()
            del Conversation._instances[instance_id]  # Clear the instance from the registry

    @patch('saccessco.ai.AIEngine')  # Mock the AIEngine dependency
    @patch('channels.layers.get_channel_layer')  # Mock the channel layer dependency
    def test_conversation_instance_management(self, mock_get_channel_layer, mock_ai_engine):
        """
        Tests that Conversation(id) returns an existing instance if available,
        or creates a new one.
        """
        # Mock the return value of get_channel_layer
        mock_get_channel_layer.return_value = InMemoryChannelLayer()
        # Mock the AIEngine constructor
        mock_ai_engine.return_value = MagicMock()

        conv1 = Conversation(conversation_id="test_id_1")
        self.assertEqual(conv1.id, "test_id_1")
        self.assertTrue(conv1._initialized)  # Should be True after __init__ completes

        conv2 = Conversation(conversation_id="test_id_1")
        self.assertEqual(conv2.id, "test_id_1")
        self.assertIs(conv1, conv2)  # Verify that conv1 and conv2 are the same object

        conv3 = Conversation(conversation_id="test_id_2")
        self.assertEqual(conv3.id, "test_id_2")
        self.assertIsNot(conv1, conv3)  # Verify they are different objects
        self.assertTrue(conv3._initialized)  # Should be True after __init__ completes

    @patch('saccessco.conversation.AIEngine')
    @patch('channels.layers.get_channel_layer')
    def test_page_change_calls_ai_engine(self, mock_get_channel_layer, mock_ai_engine_cls):
        """
        Tests that page_change method correctly calls AIEngine.respond
        and AIEngine.add_message_to_history.
        """
        # Setup mocks
        mock_channel_layer = InMemoryChannelLayer()
        mock_get_channel_layer.return_value = mock_channel_layer

        mock_ai_engine_instance = MagicMock()
        mock_ai_engine_cls.return_value = mock_ai_engine_instance
        mock_ai_engine_instance.respond.return_value = "Mocked page analysis content"

        # Create Conversation instance
        conv = Conversation(conversation_id="page_change_test")

        test_html = "<html><body>New content</body></html>"
        conv.page_change(test_html)

        # Wait for the executor task to complete
        # The _inner function is submitted to the executor, so we need to wait for its Future
        # Since _inner is a nested function, we can't directly get its Future from the submit call
        # A simple time.sleep is often sufficient for unit tests with a small executor
        # For more robust waiting, you might need to modify Conversation to expose the Future,
        # or use a more advanced threading/asyncio synchronization primitive.
        time.sleep(0.1)  # Give a small moment for the thread to run

        # Assert AIEngine.respond was called
        mock_ai_engine_instance.respond.assert_called_once_with(User, f"PAGE CHANGE\n{test_html}")

        # Assert AIEngine.add_message_to_history was called
        mock_ai_engine_instance.add_message_to_history.assert_called_once_with(Model, "Mocked page analysis content")

    @patch('saccessco.conversation.AIEngine')
    @patch('saccessco.conversation.get_channel_layer')
    @patch('saccessco.conversation.async_to_sync') # <--- ADD THIS DECORATOR HERE
    def test_user_prompt_calls_ai_engine_and_sends_websocket(self, mock_async_to_sync, mock_get_channel_layer, mock_ai_engine_cls):
        # IMPORTANT: The order of arguments in the test method must match
        # the reverse order of the decorators.
        # So, 'mock_async_to_sync' corresponds to the last decorator added.

        # Setup mocks for channel layer and its methods
        mock_channel_layer_instance = MagicMock(spec=InMemoryChannelLayer)
        # REMOVE OR COMMENT OUT THIS LINE, as we are now patching async_to_sync itself
        # mock_channel_layer_instance.group_send = AsyncMock()

        mock_get_channel_layer.return_value = mock_channel_layer_instance # get_channel_layer will return this mock instance

        # Configure mock_async_to_sync:
        # It should return a synchronous callable mock that will be called with group_send's arguments
        mock_sync_group_send_callable = MagicMock() # This will receive the final arguments
        mock_async_to_sync.return_value = mock_sync_group_send_callable

        # Setup mocks for AIEngine
        mock_ai_engine_instance = MagicMock()
        mock_ai_engine_cls.return_value = mock_ai_engine_instance
        mock_ai_response_dict = {
            "execute": ["action1", "action2"],
            "speak": "This is a mock AI response for the user."
        }
        mock_ai_engine_instance.respond.return_value = json.dumps(mock_ai_response_dict)

        # Create Conversation instance
        conv = Conversation(conversation_id="user_prompt_test")

        # --- DEBUGGING ID PRINT (Keep for verification if needed) ---
        print(f"\nDEBUG Test: mock_ai_engine_instance ID (main thread): {id(mock_ai_engine_instance)}")
        print(f"DEBUG Test: conv.ai_engine ID (after Conversation init): {id(conv.ai_engine)}")
        # --- END DEBUGGING ID PRINT ---

        test_prompt = "What's the weather like?"
        user_prompt_future = conv.user_prompt(test_prompt)
        user_prompt_future.result(timeout=5) # Wait for the thread to complete

        # --- DEBUGGING CALL COUNT PRINT (Keep for verification if needed) ---
        print(f"DEBUG Test: mock_ai_engine_instance.respond call count before assert: {mock_ai_engine_instance.respond.call_count}")
        # --- END DEBUGGING CALL COUNT PRINT ---

        # Assert AIEngine calls (these should now pass)
        mock_ai_engine_instance.respond.assert_called_once_with(User, test_prompt)
        mock_ai_engine_instance.add_message_to_history.assert_called_once_with(Model, json.dumps(mock_ai_response_dict))

        # --- NEW ASSERTIONS FOR CHANNEL LAYER INTERACTION ---
        # 1. Assert that async_to_sync was called with the correct async method (group_send)
        # mock_async_to_sync.assert_called_once_with(mock_channel_layer_instance.group_send)

        # 2. Assert that the *synchronous callable* returned by async_to_sync was called
        expected_group_name = f"{AiConsumer.GROUP_NAME_PREFIX}{conv.id}"
        expected_payload_for_channel_layer = {
            'type': 'ai_response',
            'ai_response': mock_ai_response_dict,
        }
        mock_sync_group_send_callable.assert_called_once_with(
            expected_group_name,
            expected_payload_for_channel_layer
        )
        # --- END NEW ASSERTIONS ---

    @patch('saccessco.conversation.AIEngine')
    @patch('channels.layers.get_channel_layer')
    def test_user_prompt_json_parsing_error(self, mock_get_channel_layer, mock_ai_engine_cls):
        """
        Tests error handling when AIEngine returns invalid JSON.
        Should send a simplified error object via websocket.
        """
        # Setup mocks
        # Patch get_channel_layer to return a simple MagicMock (without spec for flexibility)
        mock_channel_layer_instance_returned_by_get = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer_instance_returned_by_get

        mock_ai_engine_instance = MagicMock()
        mock_ai_engine_cls.return_value = mock_ai_engine_instance
        # Mock AI response as invalid JSON
        mock_ai_engine_instance.respond.return_value = "This is not valid JSON."

        # Create Conversation instance.
        # At this point, conv.channel_layer will be mock_channel_layer_instance_returned_by_get
        conv = Conversation(conversation_id="json_error_test")

        test_prompt = "Generate something invalid"

        # --- CRITICAL CHANGE HERE: Use patch.object to mock group_send directly on the instance ---
        with patch.object(conv.channel_layer, 'group_send', new_callable=MagicMock) as mock_group_send_method:
            user_prompt_future = conv.user_prompt(test_prompt)
            user_prompt_future.result(timeout=5) # Wait for the background thread to complete

            # Assert AIEngine.respond was called
            mock_ai_engine_instance.respond.assert_called_once_with(User, test_prompt)

            # Assert AIEngine.add_message_to_history was called (even with invalid response)
            mock_ai_engine_instance.add_message_to_history.assert_called_once_with(Model, "This is not valid JSON.")

            # Assert mock_group_send_method (the one we patched directly) was called
            expected_group_name = f"{AiConsumer.GROUP_NAME_PREFIX}{conv.id}"
            mock_group_send_method.assert_called_once()
            args, kwargs = mock_group_send_method.call_args
            self.assertEqual(args[0], expected_group_name)

            sent_payload = args[1]
            self.assertEqual(sent_payload['type'], 'ai_response')
            self.assertIn('error', sent_payload['ai_response'])
            self.assertEqual(sent_payload['ai_response']['error'], 'JSON parsing failed')
            self.assertIn('details', sent_payload['ai_response'])
            self.assertIn('raw_ai_response', sent_payload['ai_response'])
            self.assertTrue(sent_payload['ai_response']['raw_ai_response'].startswith("This is not valid JSON."))
        # --- END CRITICAL CHANGE ---

    @patch('saccessco.conversation.AIEngine')
    @patch('channels.layers.get_channel_layer')
    def test_shutdown_executor(self, mock_get_channel_layer, mock_ai_engine_cls):
        """
        Tests that the shutdown method correctly shuts down the ThreadPoolExecutor.
        """
        # Setup mocks
        mock_get_channel_layer.return_value = MagicMock(spec=InMemoryChannelLayer)
        mock_ai_engine_cls.return_value = MagicMock()

        conv = Conversation(conversation_id="shutdown_test")

        # Replace the real executor with a mock and ensure it has _shutdown
        executor_mock = MagicMock(spec=ThreadPoolExecutor)
        executor_mock._shutdown = False  # Important: Mock this attribute for tearDown to work
        conv.executor = executor_mock

        conv.shutdown()
        executor_mock.shutdown.assert_called_once_with(wait=True)
