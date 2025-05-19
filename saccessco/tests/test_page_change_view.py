# your_app_name/tests/test_page_change_view.py
# Replace 'your_app_name' with the actual name of your Django app
# Make sure this file is located within your app's 'tests' directory

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock # For mocking AIEngine

# Import your views (adjust import path if necessary)
from saccessco.views import PageChangeAPIView

# Import your serializers (optional, but good for reference)
from saccessco.serializers import PageChangeSerializer

# Import your AIEngine and roles (for mocking and checking calls)
from saccessco.ai import AIEngine, System, User # Assuming System and User roles are here


class PageChangeAPIViewTests(TestCase):
    """
    Unit tests for the PageChangeAPIView.
    """

    def setUp(self):
        """
        Set up the test client and URL.
        """
        self.client = APIClient()
        # Use the URL name defined in your urls.py
        self.url = reverse('page_change') # Matches path('saccessco/page_change/', ..., name='page_change')

    @patch('saccessco.views.AIEngine') # Patch the AIEngine class in the views module
    def test_post_valid_data_success(self, MockAIEngine):
        """
        Test POST request with valid page change data.
        Verifies 200 OK response and AIEngine interaction.
        """
        # Create a mock instance of AIEngine
        mock_engine_instance = MockAIEngine.return_value

        valid_payload = {'html': '<html><body>Valid HTML content</body></html>'}
        response = self.client.post(self.url, valid_payload, format='json')

        # Assert that the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response body contains the expected success message
        self.assertEqual(response.data, {"message": "Page change received successfully", "status": "success"})

        # Assert that AIEngine was instantiated
        MockAIEngine.assert_called_once()

        # Assert that add_message was called on the AIEngine instance
        # Check the arguments passed to add_message
        expected_message_content = f"PAGE CHANGE\n{valid_payload['html']}"
        mock_engine_instance.add_message.assert_called_once_with(System, expected_message_content)


    @patch('saccessco.views.AIEngine') # Patch AIEngine for this test too
    def test_post_invalid_data_missing_key(self, MockAIEngine):
        """
        Test POST request with invalid data (missing 'page_change' key).
        Verifies 400 Bad Request response and serializer errors.
        """
        invalid_payload = {'other_key': 'some_value'}
        response = self.client.post(self.url, invalid_payload, format='json')

        # Assert that the response status code is 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert that the response body contains validation errors from the serializer
        self.assertIn('html', response.data)
        self.assertIn('This field is required.', response.data['html'])

        # Assert that AIEngine was NOT instantiated or interacted with
        MockAIEngine.assert_not_called()


    @patch('saccessco.views.AIEngine') # Patch AIEngine
    def test_post_invalid_data_empty_html(self, MockAIEngine):
        """
        Test POST request with invalid data (empty 'page_change' string).
        Verifies 400 Bad Request response due to serializer validation.
        """
        invalid_payload = {'html': ''}
        response = self.client.post(self.url, invalid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('html', response.data)
        # Check the specific error message from your serializer's custom validation
        self.assertIn('This field may not be blank.', response.data['html'])

        # Assert that AIEngine was NOT instantiated or interacted with
        MockAIEngine.assert_not_called()


    @patch('saccessco.views.AIEngine') # Patch AIEngine
    def test_post_invalid_data_not_json(self, MockAIEngine):
        """
        Test POST request with non-JSON data.
        Verifies 400 Bad Request response from DRF's parser.
        """
        invalid_payload = "This is not valid JSON"
        # Sending with format='text' or default will cause DRF's JSONParser to fail
        response = self.client.post(self.url, invalid_payload, format='json') # Use format='text' to send as plain text

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The exact error message can vary, but it should indicate a parsing issue
        self.assertIn('non_field_errors', response.data)
        self.assertIn('Invalid data. Expected a dictionary, but got str.',str(response.data['non_field_errors'][0])) # Check for a message indicating parsing failure

        # Assert that AIEngine was NOT instantiated or interacted with
        MockAIEngine.assert_not_called()

