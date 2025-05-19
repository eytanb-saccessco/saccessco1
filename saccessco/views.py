# views.py
from rest_framework.views import APIView

from rest_framework.response import Response
from rest_framework import status

from .ai import AIEngine, System, User
from .serializers import PageChangeSerializer, UserPromptSerializer
from django_q.tasks import async_task
from .tasks import ai_call

class PageChangeAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = PageChangeSerializer(data=request.data)
        if serializer.is_valid():
            page_change_html = serializer.validated_data['html']

            AIEngine().add_message(System, f"PAGE CHANGE\n{page_change_html}")

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
            user_prompt = serializer.validated_data['prompt']
            AIEngine().add_message(User, user_prompt)
            task_id = async_task(ai_call, AIEngine().get_conversation())

            return Response(
                {"message": f"User prompt received. Ai response in progress, task_id: {task_id} ", "status": "success"},
                status=status.HTTP_200_OK
            )
        else:
            # If the data is not valid, return the errors
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

