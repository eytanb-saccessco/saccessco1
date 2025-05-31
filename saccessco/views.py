# saccessco/views.py
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
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
        logger.info(f"UserPromptAPIView called with {request.data}")
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

class PageManipulatorTestPageView(TemplateView):
    template_name = 'page_manipulator_test_page.html'

@method_decorator(csrf_exempt, name='dispatch')
class FormSubmitSuccessView(TemplateView):
    template_name = 'form_submit_success_page.html'

    # The default get() method is inherited from TemplateView and handles GET requests.
    # We are adding a post() method to handle POST requests.


    def post(self, request, *args, **kwargs):
        logger.info(f"FormSubmitSuccessView received a POST request.")
        logger.info(f"POST data: {request.POST}")

        # --- IMPORTANT CONSIDERATIONS FOR POST REQUESTS ---
        # 1. Process the form data:
        #    If your form sends data (e.g., from the 'formInput' field in your HTML),
        #    you can access it via request.POST.
        form_data_value = request.POST.get('form_data', 'No data received from formInput')
        logger.info(f"Value of 'form_data': {form_data_value}")

        # 2. Perform any necessary actions:
        #    This is where you would typically save data to a database,
        #    perform calculations, send emails, etc.
        #    For a simple "success" page, you might not need complex logic.

        # 3. Post-redirect-get (PRG) pattern:
        #    It's a best practice to redirect the user after a successful POST request.
        #    This prevents issues like:
        #    - User refreshing the page and resubmitting the form.
        #    - Browser back button causing form resubmission.
        #    By redirecting to a GET request of the same success page (or another page),
        #    you ensure the browser history is clean and a refresh only reloads the GET.

        # Redirect to the GET version of this same success page
        # 'form_submit_success' is the name you defined in your urls.py for this view.
        return redirect('form_submit_success')

        # --- ALTERNATIVE (Less Recommended for Success Pages) ---
        # If you did NOT want to redirect and instead just render the template directly:
        # return render(request, self.template_name, {'message': 'Your form was processed!'})
        # This would directly render the template without a new GET request.
        # However, it keeps the POST request in the browser's history, which can lead to
        # the issues mentioned above if the user refreshes or uses the back button.