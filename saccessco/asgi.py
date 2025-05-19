# asgi.py
# This file is the entry point for ASGI-compatible web servers (like Daphne or Uvicorn).

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Import your routing configuration
import saccessco.routing # Replace 'your_app_name'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings') # Replace 'your_project_name'

# Get the standard Django WSGI application
django_asgi_app = get_asgi_application()

# Define the main ASGI application
application = ProtocolTypeRouter({
    # Handle standard HTTP requests using the Django WSGI application
    "http": django_asgi_app,

    # Handle WebSocket requests
    "websocket": AuthMiddlewareStack( # Optional: Add AuthMiddlewareStack if you need user authentication in consumers
        URLRouter(
            saccessco.routing.websocket_urlpatterns # Replace 'your_app_name'
        )
    ),

    # You can add other protocols here if needed
})
