from django.urls import re_path, path

from . import consumers # Import your consumers

websocket_urlpatterns = [
    re_path(r'^ws/saccessco/ai/(?P<conversation_id>[^/]+)/$', consumers.AiConsumer.as_asgi()),
    # re_path(r'.*', consumers.AiConsumer.as_asgi()),
    # path('/saccesco/ai/', consumers.AiConsumer.as_asgi()),
    # re_path(r'^saccesco/ai/?$', consumers.AiConsumer.as_asgi()),
    # re_path(r'^(?:/)?saccesco/ai/?$', consumers.AiConsumer.as_asgi()),
    # re_path(r'^saccesco/ai/$', consumers.AiConsumer.as_asgi()),
]

