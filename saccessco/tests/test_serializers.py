# your_app_name/tests/test_serializers.py
# Replace 'your_app_name' with the actual name of your Django app

from django.test import TestCase
from rest_framework.exceptions import ValidationError

# Import your serializers from your app's serializers.py
from saccessco.serializers import PageChangeSerializer, UserPromptSerializer


class PageChangeSerializerTests(TestCase):
    """
    Unit tests for the PageChangeSerializer.
    """

    def test_valid_data(self):
        """
        Test serializer with valid data.
        """
        data = {'html': '<html><body><h1>Test</h1></body></html>',
                'conversation_id': 'test_conversation_id',}
        serializer = PageChangeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_missing_html_key(self):
        """
        Test serializer when the 'html' key is missing.
        """
        data = {'other_key': 'some_value'}
        serializer = PageChangeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('html', serializer.errors) # Check if 'html' is in the errors
        self.assertIn('This field is required.', serializer.errors['html']) # Check specific error message

    def test_html_is_empty_string(self):
        """
        Test custom validation for empty 'html' string.
        """
        data = {'html': '', 'conversation_id': 'test_conversation_id'}
        serializer = PageChangeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('html', serializer.errors)
        self.assertIn('This field may not be blank.', serializer.errors['html'])

    def test_html_is_whitespace_only(self):
        """
        Test custom validation for whitespace-only 'html' string.
        """
        data = {'html': '   \n ', 'conversation_id': 'test_conversation_id'}
        serializer = PageChangeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('html', serializer.errors)
        self.assertIn('This field may not be blank.', serializer.errors['html'])


class UserPromptSerializerTests(TestCase):
    """
    Unit tests for the UserPromptSerializer.
    """

    def test_valid_data(self):
        """
        Test serializer with valid data.
        """
        data = {'prompt': 'Hello AI!', 'conversation_id': 'test_conversation_id'}
        serializer = UserPromptSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_missing_prompt_key(self):
        """
        Test serializer when the 'prompt' key is missing.
        """
        data = {'message': 'some_message', 'conversation_id': 'test_conversation_id'}
        serializer = UserPromptSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('prompt', serializer.errors)
        self.assertIn('This field is required.', serializer.errors['prompt'])

    def test_prompt_is_not_string(self):
        """
        Test serializer when 'prompt' value is not a string.
        """
        data = {'prompt': ['list', 'instead'], 'conversation_id': 'test_conversation_id'}
        serializer = UserPromptSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('prompt', serializer.errors)
        self.assertIn('Not a valid string.', serializer.errors['prompt'])

    def test_prompt_is_empty_string(self):
        """
        Test custom validation for empty 'prompt' string.
        """
        data = {'prompt': '', 'conversation_id': 'test_conversation_id'}
        serializer = UserPromptSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('prompt', serializer.errors)
        self.assertIn('This field may not be blank.', serializer.errors['prompt'])

    def test_prompt_is_whitespace_only(self):
        """
        Test custom validation for whitespace-only 'prompt' string.
        """
        data = {'prompt': ' \t ', 'conversation_id': 'test_conversation_id'}
        serializer = UserPromptSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('prompt', serializer.errors)
        self.assertIn('This field may not be blank.', serializer.errors['prompt'])

