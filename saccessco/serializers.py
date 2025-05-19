# serializers.py
from rest_framework import serializers

class PageChangeSerializer(serializers.Serializer):
    html = serializers.CharField(
        help_text="The HTML content of the page change."
    )

    def validate_html(self, value):
        print(f"html value: {value} type: {type(value)}")
        if not value or not value.strip():
            raise serializers.ValidationError("Html content cannot be empty.")
        if not isinstance(value, str):
            raise serializers.ValidationError("Html content must be a string.")
        return value

class UserPromptSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        help_text="The user prompt."
    )
    def validate_prompt(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty.")
        return value

