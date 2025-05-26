# asgi.py
# This file is the entry point for ASGI-compatible web servers (like Daphne or Uvicorn).

import os
import logging

# Removed AuthMiddlewareStack import for this minimal test
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Import your routing configuration
# IMPORTANT: Replace 'your_project_name' with the actual name of your Django project
# and 'saccessco' with the actual name of your Django app where routing.py resides.
import saccessco.routing # Assuming your app is named 'saccessco'

# Replace 'your_project_name' with the actual name of your Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saccessco.settings')

# Get the standard Django WSGI application
django_asgi_app = get_asgi_application()

# Set up a logger for ASGI debugging
logger = logging.getLogger("saccessco")


# Define the main ASGI application
application = ProtocolTypeRouter({
    # Handle standard HTTP requests using the Django WSGI application
    "http": django_asgi_app,

    # Handle WebSocket requests
    "websocket": URLRouter( # Directly use URLRouter without any middleware for testing
        saccessco.routing.websocket_urlpatterns
    ),

    # You can add other protocols here if needed
})

# --- DEBUGGING AID ---
# Print the loaded WebSocket URL patterns to the console when asgi.py is loaded
logger.info("\n--- Loaded WebSocket URL Patterns ---")
for pattern in saccessco.routing.websocket_urlpatterns:
    print(f"  Pattern: {pattern.pattern.regex.pattern}")
logger.info("-------------------------------------\n")
