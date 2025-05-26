# saccessco/tests/test_views.py

import json
from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
import logging

# Configure logging for tests (optional, but good for debugging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("saccessco")


class APIViewTests(APITestCase):
    """
    Unit tests for PageChangeAPIView and UserPromptAPIView.
    """

    def setUp(self):
        # Clear Conversation instances to ensure test isolation
        from saccessco.conversation import Conversation
        Conversation._instances = {}

    # --- Tests for PageChangeAPIView ---

    @patch('saccessco.views.PageChangeSerializer')
    @patch('saccessco.views.Conversation')
    def test_page_change_success(self, MockConversation, MockPageChangeSerializer):
        """
        Test POST request to PageChangeAPIView with valid data.
        """
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = True
        mock_serializer_instance.data = {"conversation_id": "test_conv_123"}
        mock_serializer_instance.validated_data = {"conversation_id": "test_conv_123", "html": "<html>mock_html</html>"}
        MockPageChangeSerializer.return_value = mock_serializer_instance

        mock_conversation_instance = MagicMock()
        MockConversation.return_value = mock_conversation_instance

        # Ensure page_change returns a Future mock, but the view does NOT call .result() on it.
        mock_future = MagicMock()
        mock_conversation_instance.page_change.return_value = mock_future
        # mock_future.result.return_value = None # This line is no longer relevant for the view test

        data = {
            "conversation_id": "test_conv_123",
            "html": "<html>some_html_content</html>"
        }
        # --- CORRECT URL NAME ---
        url = reverse('page_change')

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Page change received successfully", "status": "success"})

        MockPageChangeSerializer.assert_called_once_with(data=data)
        mock_serializer_instance.is_valid.assert_called_once_with()

        MockConversation.assert_called_once_with(conversation_id="test_conv_123")
        mock_conversation_instance.page_change.assert_called_once_with("<html>mock_html</html>")

        # --- REMOVED THIS ASSERTION ---
        # mock_future.result.assert_called_once_with(timeout=None)

    @patch('saccessco.views.PageChangeSerializer')
    @patch('saccessco.views.Conversation')
    def test_page_change_invalid_data(self, MockConversation, MockPageChangeSerializer):
        """
        Test POST request to PageChangeAPIView with invalid data.
        """
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = False
        mock_serializer_instance.errors = {"html": ["This field is required."]}
        MockPageChangeSerializer.return_value = mock_serializer_instance

        data = {
            "conversation_id": "test_conv_123",
        }
        # --- CORRECT URL NAME ---
        url = reverse('page_change')

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"html": ["This field is required."]})

        MockPageChangeSerializer.assert_called_once_with(data=data)
        mock_serializer_instance.is_valid.assert_called_once_with()

        MockConversation.assert_not_called()

    # --- Tests for UserPromptAPIView ---

    @patch('saccessco.views.UserPromptSerializer')
    @patch('saccessco.views.Conversation')
    def test_user_prompt_success(self, MockConversation, MockUserPromptSerializer):
        """
        Test POST request to UserPromptAPIView with valid data.
        """
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = True
        mock_serializer_instance.data = {"conversation_id": "test_conv_456"}
        mock_serializer_instance.validated_data = {"conversation_id": "test_conv_456", "prompt": "Hello AI!"}
        MockUserPromptSerializer.return_value = mock_serializer_instance

        mock_conversation_instance = MagicMock()
        MockConversation.return_value = mock_conversation_instance

        # Ensure user_prompt returns a Future mock, but the view does NOT call .result() on it.
        mock_future = MagicMock()
        mock_conversation_instance.user_prompt.return_value = mock_future
        # mock_future.result.return_value = None # This line is no longer relevant for the view test

        data = {
            "conversation_id": "test_conv_456",
            "prompt": "What's the weather like?"
        }
        # --- CORRECT URL NAME ---
        url = reverse('user_prompt')

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # --- UPDATED ASSERTION FOR THE NEW RETURN VALUE ---
        self.assertEqual(response.data, {"message": "User prompt received successfully", "status": "success"})

        MockUserPromptSerializer.assert_called_once_with(data=data)
        mock_serializer_instance.is_valid.assert_called_once_with()

        MockConversation.assert_called_once_with(conversation_id="test_conv_456")
        mock_conversation_instance.user_prompt.assert_called_once_with("Hello AI!")

        # --- REMOVED THIS ASSERTION ---
        # mock_future.result.assert_called_once_with(timeout=None)

    @patch('saccessco.views.UserPromptSerializer')
    @patch('saccessco.views.Conversation')
    def test_user_prompt_invalid_data(self, MockConversation, MockUserPromptSerializer):
        """
        Test POST request to UserPromptAPIView with invalid data.
        """
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.is_valid.return_value = False
        mock_serializer_instance.errors = {"prompt": ["This field cannot be blank."]}
        MockUserPromptSerializer.return_value = mock_serializer_instance

        data = {
            "conversation_id": "test_conv_456",
        }
        # --- CORRECT URL NAME ---
        url = reverse('user_prompt')

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"prompt": ["This field cannot be blank."]})

        MockUserPromptSerializer.assert_called_once_with(data=data)
        mock_serializer_instance.is_valid.assert_called_once_with()

        MockConversation.assert_not_called()

