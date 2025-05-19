# your_app_name/routing.py
# Replace 'your_app_name'

from django.urls import re_path

from . import consumers # Import your consumers

websocket_urlpatterns = [
    # This pattern will match WebSocket connections to ws://your_domain/ws/chat/<room_name>/
    # You can adjust the URL pattern to include parameters needed to identify the conversation or user.
    # For your case, maybe something like ws://your_domain/ws/conversation/<conversation_id>/
    re_path(r'ws/saccesco/ai/$', consumers.AiConsumer.as_asgi()),

    # You can add other WebSocket URL patterns here
]
