# your_app_name/tests/test_tasks.py
# Replace 'your_app_name' with the actual name of your Django app
# Make sure this file is located within your app's 'tests' directory

import asynctest # Requires 'pip install asynctest'
from unittest.mock import patch, MagicMock
from saccessco.consumers import WEB_SOCKET_GROUP_NAME

# Import your async task function
from saccessco.tasks import ai_call

# Define the path to the task function for patching if needed elsewhere
AI_TASK_PATH = 'saccessco.tasks.ai_call'

# Define the path to the fixed group name in consumers.py for patching
WEB_SOCKET_GROUP_NAME_PATH = 'saccessco.consumers.WEB_SOCKET_GROUP_NAME'

# Define the path to the AIEngine for patching
AI_ENGINE_PATH = 'saccessco.tasks.AIEngine'

# Define the path to the logger for patching
LOGGER_PATH = 'saccessco.tasks.logger' # Patch the logger instance used in tasks.py


class AiCallTaskTests(asynctest.TestCase):
    """
    Unit tests for the ai_call async task.
    """

    @patch(LOGGER_PATH) # This mock will be the LAST argument in the method
    @patch('saccessco.tasks.get_channel_layer') # This mock will be the SECOND TO LAST argument
    @patch(AI_ENGINE_PATH) # This mock will be the THIRD TO LAST argument
    async def test_ai_call_success_sends_message(self,
                                                 MockAIEngine,
                                                 mock_get_channel_layer,
                                                 mock_logger):
        """
        Test successful execution of ai_call task where channel layer is available.
        Verifies AIEngine interaction and message sending via channel layer.
        """
        # --- Configure Mocks ---
        # Mock AIEngine instance and its methods
        mock_engine_instance = MockAIEngine.return_value
        mock_ai_response = "This is a mock AI response."
        mock_engine_instance.respond.return_value = mock_ai_response

        # Mock the channel layer instance and its group_send method
        mock_channel_layer_instance = MagicMock() # Use MagicMock for async methods
        mock_channel_layer_instance.group_send = asynctest.CoroutineMock() # Mock group_send as a coroutine mock
        mock_get_channel_layer.return_value = mock_channel_layer_instance

        # Dummy conversation data for the task argument
        test_conversation = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'system', 'content': 'Hi there!'}
        ]

        # --- Call the async task ---
        # Await the task function since it's an async function
        result = await ai_call(test_conversation)

        # --- Assertions ---
        # Assert that AIEngine was instantiated once
        MockAIEngine.assert_called_once()

        # Assert that set_conversation was called on the AIEngine instance with the correct data
        mock_engine_instance.set_conversation.assert_called_once_with(test_conversation)

        # Assert that respond was called on the AIEngine instance once
        mock_engine_instance.respond.assert_called_once()

        # Assert that get_channel_layer was called once
        mock_get_channel_layer.assert_called_once()

        # Assert that channel_layer.group_send was called once
        mock_channel_layer_instance.group_send.assert_called_once()

        # Assert that channel_layer.group_send was called with the correct arguments
        # The first argument is the group name (mocked as 'mock_ai_group')
        # The second argument is the message dictionary
        mock_channel_layer_instance.group_send.assert_called_once_with(
            'ai_response', # Check against the mocked group name
            mock_ai_response
        )

        # Assert that the task returned the AI response string
        self.assertEqual(result, mock_ai_response)

        # Assert that logger.error was NOT called
        mock_logger.error.assert_not_called()


    @patch(LOGGER_PATH) # LAST argument
    @patch('saccessco.tasks.get_channel_layer') # SECOND TO LAST argument
    @patch(AI_ENGINE_PATH) # THIRD TO LAST argument
    async def test_ai_call_no_channel_layer(self, MockAIEngine, mock_get_channel_layer, mock_logger):
        """
        Test execution of ai_call task when channel layer is NOT configured/available.
        Verifies AIEngine interaction and no message sending, with error logging.
        """
        # --- Configure Mocks ---
        # Mock AIEngine instance and its methods
        mock_engine_instance = MockAIEngine.return_value
        mock_ai_response = "Mock response even without channels."
        mock_engine_instance.respond.return_value = mock_ai_response

        # Configure get_channel_layer to return None
        mock_get_channel_layer.return_value = None

        # Dummy conversation data
        test_conversation = [{'role': 'user', 'content': 'Test'}]

        # --- Call the async task ---
        result = await ai_call(test_conversation)

        # --- Assertions ---
        # Assert that AIEngine was instantiated and methods called
        MockAIEngine.assert_called_once()
        mock_engine_instance.set_conversation.assert_called_once_with(test_conversation)
        mock_engine_instance.respond.assert_called_once()

        # Assert that get_channel_layer was called once
        mock_get_channel_layer.assert_called_once()

        # Assert that channel_layer.group_send was NOT called
        # We need to check if the mock instance was ever created and if its method was called
        # Since get_channel_layer returns None, the mock_channel_layer_instance is never created.
        # We can assert that if get_channel_layer returned a mock, group_send wouldn't be called on it.
        # A simpler check is just to ensure the mock returned by get_channel_layer (which is None)
        # doesn't have group_send called on it, but patching get_channel_layer to return None
        # means we can't assert on methods of the return value directly.
        # The most direct check is that the code path for group_send wasn't taken.
        # We can check this by ensuring the mock_channel_layer_instance (which would be None)
        # was not used to call group_send. The previous assertion on group_send.assert_called_once()
        # would fail if get_channel_layer returned None, which is what we want.

        # Assert that logger.error was called once with the expected message
        mock_logger.error.assert_called_once_with(
            "Task: Channel layer is not configured or available. Could not send AI response."
        )

        # Assert that the task still returned the AI response
        self.assertEqual(result, mock_ai_response)


    @patch(LOGGER_PATH) # LAST argument
    @patch('saccessco.tasks.get_channel_layer') # SECOND TO LAST argument
    @patch(AI_ENGINE_PATH) # THIRD TO LAST argument
    async def test_ai_call_aiengine_exception(self, MockAIEngine, mock_get_channel_layer, mock_logger):
        """
        Test execution of ai_call task when AIEngine.respond raises an exception.
        Verifies exception handling and error logging.
        """
        # --- Configure Mocks ---
        # Mock AIEngine instance and make its respond method raise an exception
        mock_engine_instance = MockAIEngine.return_value
        test_exception = Exception("Mock AI Engine Error")
        mock_engine_instance.respond.side_effect = test_exception # Make respond raise the exception

        # Mock the channel layer (it won't be used in this case)
        mock_channel_layer_instance = MagicMock()
        mock_channel_layer_instance.group_send = asynctest.CoroutineMock()
        mock_get_channel_layer.return_value = mock_channel_layer_instance

        # Dummy conversation data
        test_conversation = [{'role': 'user', 'content': 'Error prompt'}]

        # --- Call the async task and expect an exception ---
        # Use assert_raises to check that the expected exception is raised
        with self.assertRaises(Exception) as cm:
            await ai_call(test_conversation)

        # Assert the raised exception is the one we mocked
        self.assertEqual(cm.exception, test_exception)

        # --- Assertions ---
        # Assert that AIEngine was instantiated and set_conversation called
        MockAIEngine.assert_called_once()
        mock_engine_instance.set_conversation.assert_called_once_with(test_conversation)

        # Assert that respond was called (which raised the exception)
        mock_engine_instance.respond.assert_called_once()

        # Assert that get_channel_layer was called (before the exception)
        mock_get_channel_layer.assert_called_once()

        # Assert that channel_layer.group_send was NOT called
        mock_channel_layer_instance.group_send.assert_not_called()

        # Assert that logger.error was called once with the expected message
        # Note: Your original logger call had an incorrect f-string format.
        # We'll check for a message that indicates an error occurred.
        # The exact message logged depends on your logger configuration and how
        # the exception is formatted in the log call. Assuming it includes the exception type/message.
        # You might need to adjust the assertion based on the exact log output.
        mock_logger.error.assert_called_once()
        # Optional: Check the arguments of the logger call more specifically
        # For example, check if the first argument is a string containing 'Error in Django-Q task'
        # self.assertIn('Error in Django-Q task', mock_logger.error.call_args[0][0])
        # self.assertIn(str(test_exception), str(mock_logger.error.call_args[0][0]))


    # Note: Your original logger call in the except block had a formatting issue:
    # logger.error("Error in Django-Q task process_conversation_and_send_response : {e}")
    # This should ideally be:
    # logger.error("Error in Django-Q task process_conversation_and_send_response: %s", e)
    # or
    # logger.exception("Error in Django-Q task process_conversation_and_send_response:")
    # The current test mocks the logger call based on the provided code, but fixing
    # the logging format in tasks.py is recommended.

