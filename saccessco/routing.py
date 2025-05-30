from django.urls import re_path, path

from . import consumers # Import your consumers

websocket_urlpatterns = [
    re_path(r'^ws/saccessco/ai/(?P<conversation_id>[^/]+)/$', consumers.AiConsumer.as_asgi()),
]

