# your_app_name/tests/test_user_prompt_view.py
# Replace 'your_app_name' with the actual name of your Django app
# Make sure this file is located within your app's 'tests' directory

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock # For mocking AIEngine and async_task

# Import your views (adjust import path if necessary)
from saccessco.views import UserPromptAPIView

# Import your serializers (optional, but good for reference)
from saccessco.serializers import UserPromptSerializer

# Import your AIEngine and roles (for mocking and checking calls)
from saccessco.ai import AIEngine, System, User # Assuming System and User roles are here

# Import the task function path (adjust import path if necessary)
# Assuming your task is in your_app_name/tasks.py and named ai_call
AI_TASK_PATH = 'saccessco.tasks.ai_call'


class UserPromptAPIViewTests(TestCase):
    """
    Unit tests for the UserPromptAPIView.
    """

    def setUp(self):
        """
        Set up the test client and URL.
        """
        self.client = APIClient()
        # Use the URL name defined in your urls.py
        self.url = reverse('user_prompt') # Matches path('saccessco/user_prompt/', ..., name='user_prompt')

    # Patch both AIEngine and async_task for this test
    @patch('saccessco.views.AIEngine')
    @patch('saccessco.views.async_task')
    def test_post_valid_data_success_enqueues_task(self, mock_async_task, MockAIEngine):
        """
        Test POST request with valid user prompt data.
        Verifies 200 OK response, AIEngine interaction, and task enqueuing.
        """
        # Create mock instances
        mock_engine_instance = MockAIEngine.return_value
        # Configure the mock engine to return a specific conversation history
        mock_conversation_history = [
            {'role': System, 'content': 'Initial system message'},
            {'role': User, 'content': 'Previous user message'}
        ]
        mock_engine_instance.get_conversation.return_value = mock_conversation_history

        valid_payload = {
            'prompt': 'Tell me a joke',
            # Your current view doesn't explicitly require conversation_id in the payload
            # but it's good practice to include it if you plan to use it.
            # Based on your view code, it seems conversation_id is NOT used from the payload
            # when calling AIEngine or async_task. If you need conversation_id in the task,
            # you'll need to modify your view to get it from the payload and pass it.
            # For now, we'll test based on the provided view code.
        }
        response = self.client.post(self.url, valid_payload, format='json')

        # Assert that the response status code is 200 OK
        # NOTE: Your view returns 200 OK, but 202 Accepted is more appropriate for async tasks.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response body contains the expected success message
        self.assertIn("User prompt received. Ai response in progress, task_id:", response.data['message'])
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('task_id', response.data['message']) # Check that task_id is returned

        # Assert that AIEngine was instantiated
        self.assertEqual(MockAIEngine.call_count, 2)

        # Assert that add_message was called on the AIEngine instance
        # Check the arguments passed to add_message
        mock_engine_instance.add_message.assert_called_once_with(User, valid_payload['prompt'])

        # Assert that get_conversation was called on the AIEngine instance
        mock_engine_instance.get_conversation.assert_called_once()

        # Assert that async_task was called exactly once
        mock_async_task.assert_called_once()

        # Assert that async_task was called with the correct arguments
        # The first argument is the task path string
        # The second argument is the conversation history returned by get_conversation()
        expected_task_path = AI_TASK_PATH # Use the defined task path
        called_args, called_kwargs = mock_async_task.call_args

        # self.assertEqual(called_args[0], expected_task_path) # Check task path
        self.assertEqual(called_args[1], mock_conversation_history) # Check the conversation history argument


    @patch('saccessco.views.AIEngine') # Patch AIEngine for this test
    @patch('saccessco.views.async_task') # Patch async_task
    def test_post_invalid_data_missing_prompt(self, mock_async_task, MockAIEngine):
        """
        Test POST request with invalid data (missing 'user_prompt' key).
        Verifies 400 Bad Request response and serializer errors.
        """
        invalid_payload = {'other_key': 'some_value'}
        response = self.client.post(self.url, invalid_payload, format='json')

        # Assert that the response status code is 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert that the response body contains validation errors from the serializer
        self.assertIn('prompt', response.data)
        self.assertIn('This field is required.', response.data['prompt'])

        # Assert that AIEngine was NOT instantiated or interacted with
        MockAIEngine.assert_not_called()
        # Assert that async_task was NOT called
        mock_async_task.assert_not_called()


    # @patch('saccessco.views.AIEngine') # Patch AIEngine
    # @patch('saccessco.views.async_task') # Patch async_task
    # def test_post_invalid_data_empty_prompt(self, mock_async_task, MockAIEngine):
    #     """
    #     Test POST request with invalid data (empty 'user_prompt' string).
    #     Verifies 400 Bad Request response due to serializer validation.
    #     """
    #     invalid_payload = {'user_prompt': ''}
    #     response = self.client.post(self.url, invalid_payload, format='json')
    #
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertIn('user_prompt', response.data)
    #     # Check the specific error message from your serializer's custom validation
    #     self.assertIn('Prompt cannot be empty.', response.data['user_prompt'])
    #
    #     # Assert that AIEngine was NOT instantiated or interacted with
    #     MockAIEngine.assert_not_called()
    #     # Assert that async_task was NOT called
    #     mock_async_task.assert_not_called()
    #
    # @patch('saccessco.views.AIEngine') # Patch AIEngine
    # @patch('saccessco.views.async_task') # Patch async_task
    # def test_post_invalid_data_not_string(self, mock_async_task, MockAIEngine):
    #     """
    #     Test POST request with invalid data ('user_prompt' is not a string).
    #     Verifies 400 Bad Request response due to serializer validation.
    #     """
    #     invalid_payload = {'user_prompt': 123} # Integer instead of string
    #     response = self.client.post(self.url, invalid_payload, format='json')
    #
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertIn('user_prompt', response.data)
    #     # Check the specific error message from DRF's CharField
    #     self.assertIn('Not a valid string.', response.data['user_prompt'])
    #
    #     # Assert that AIEngine was NOT instantiated or interacted with
    #     MockAIEngine.assert_not_called()
    #     # Assert that async_task was NOT called
    #     mock_async_task.assert_not_called()
    #
    # @patch('saccessco.views.AIEngine') # Patch AIEngine
    # @patch('saccessco.views.async_task') # Patch async_task
    # def test_post_invalid_data_not_json(self, mock_async_task, MockAIEngine):
    #     """
    #     Test POST request with non-JSON data.
    #     Verifies 400 Bad Request response from DRF's parser.
    #     """
    #     invalid_payload = "This is not valid JSON"
    #     # Sending with format='text' or default will cause DRF's JSONParser to fail
    #     response = self.client.post(self.url, invalid_payload, format='text') # Use format='text' to send as plain text
    #
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     # The exact error message can vary, but it should indicate a parsing issue
    #     self.assertIn('detail', response.data)
    #     self.assertIn('JSON parse error', response.data['detail']) # Check for a message indicating parsing failure
    #
    #     # Assert that AIEngine was NOT instantiated or interacted with
    #     MockAIEngine.assert_not_called()
    #     # Assert that async_task was NOT called
    #     mock_async_task.assert_not_called()

