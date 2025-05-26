# saccessco/views.py
from django.views.generic import TemplateView
from rest_framework.views import APIView

from rest_framework.response import Response
from rest_framework import status

from .conversation import Conversation
from .serializers import PageChangeSerializer, UserPromptSerializer
import logging

logger = logging.getLogger("saccessco")

class PageChangeAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = PageChangeSerializer(data=request.data)
        if serializer.is_valid():
            conversation_id = serializer.data["conversation_id"]
            page_change_html = serializer.validated_data['html']

            conversation = Conversation(conversation_id=conversation_id)
            conversation.page_change(page_change_html)

            return Response(
                {"message": "Page change received successfully", "status": "success"},
                status=status.HTTP_200_OK
            )
        else:
            # If the data is not valid, return the errors
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


class UserPromptAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = UserPromptSerializer(data=request.data)
        if serializer.is_valid():
            conversation_id = serializer.data["conversation_id"]
            user_prompt = serializer.validated_data['prompt']

            conversation = Conversation(conversation_id=conversation_id)
            conversation.user_prompt(user_prompt)

            # --- ADD THIS RETURN STATEMENT ---
            return Response(
                {"message": "User prompt received successfully", "status": "success"},
                status=status.HTTP_200_OK
            )
            # --- END ADDITION ---
        else:
            # If the data is not valid, return the errors
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

class TestHtmlView(TemplateView):
    template_name = "test.html"