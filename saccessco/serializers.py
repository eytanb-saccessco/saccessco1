# serializers.py
from rest_framework import serializers

class ConversationIdSerializer(serializers.Serializer):
    conversation_id = serializers.CharField(max_length=40)
    def validate_conversation_id(self, value):
        if value is None:
            raise serializers.ValidationError("Conversation ID can't be None")
        if value == "":
            raise serializers.ValidationError("Conversation ID can't be empty")
        return value

class PageChangeSerializer(ConversationIdSerializer):
    html = serializers.CharField(
        help_text="The HTML content of the page change."
    )

    def validate_html(self, value):
        # print(f"html value: {value} type: {type(value)}")
        if not value or not value.strip():
            raise serializers.ValidationError("Html content cannot be empty.")
        if not isinstance(value, str):
            raise serializers.ValidationError("Html content must be a string.")
        return value

class UserPromptSerializer(ConversationIdSerializer):
    prompt = serializers.CharField(
        help_text="The user prompt."
    )
    def validate_prompt(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty.")
        return value

