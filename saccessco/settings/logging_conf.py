# logging_conf.py

import os
from pathlib import Path
import logging # Import logging to use it for debugging within this file

# Define the log directory. For development, it's often easier to put logs
# directly in your project root or a subfolder within it, as /var/log requires root.
# For production, /var/log/your_app_name is fine, but ensure correct permissions.

# Assuming BASE_DIR is available from settings.py, or define it here if this file
# is imported directly (e.g., BASE_DIR = Path(__file__).resolve().parent.parent)
# For simplicity, let's assume it's in the project root for now.
# If this file is in your app directory, you might need to adjust BASE_DIR.
# For this example, let's make it relative to where settings.py would be.
# A safer bet for dev is to put it in the project root.
# Let's assume your Django project root is the current working directory when Daphne runs.

# Use a log directory relative to your project's root for easier development
# You might need to adjust this if your project structure is different.
# For example, if this file is in 'saccessco/logging_conf.py', and your project root
# is 'saccessco1/', then BASE_DIR would be `Path(__file__).resolve().parent.parent.parent`
# A common pattern is to pass BASE_DIR from settings.py.
# For now, let's use a simple relative path for development.
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent # Assumes logging_conf.py is in an app folder

APP_NAME = "saccessco"
LOG_DIR = PROJECT_ROOT / "logs" # Create a 'logs' folder in your project root
LOG_DIR.mkdir(parents=True, exist_ok=True) # Ensure the directory exists

# --- DEBUGGING AID: Log the resolved paths for the file handler ---
# This logger is configured temporarily to ensure this debug message appears
# even if the main LOGGING config hasn't fully taken effect for the file handler.
temp_logger = logging.getLogger(__name__)
temp_logger.setLevel(logging.DEBUG)
temp_handler = logging.StreamHandler()
temp_formatter = logging.Formatter('{levelname} {asctime} {message}', style='{')
temp_handler.setFormatter(temp_formatter)
temp_logger.addHandler(temp_handler)
temp_logger.propagate = False # Prevent double logging if root logger also has console handler

temp_logger.debug(f"LOG_DIR resolved to: {LOG_DIR}")
temp_logger.debug(f"django.log filename resolved to: {os.path.join(LOG_DIR, 'django.log')}")
# -----------------------------------------------------------------


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # Keep Django's default loggers
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {pathname}:{lineno} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {pathname}:{lineno} {message}',
            'style': '{',
        },
    },
    'handlers': {
        f'{APP_NAME}_file': {
            'level': 'DEBUG', # Set handler level to DEBUG to capture all messages
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'), # Path to your main Django log file
            'formatter': 'verbose',
        },
        'q_file': { # NEW: Handler for Django-Q specific logs
            'level': 'INFO', # Start with INFO, can be WARNING/ERROR to reduce polling logs
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'django_q.log'), # Separate file for Q logs
            'formatter': 'verbose',
        },
        'console': { # Add a console handler for immediate feedback
            'level': 'INFO', # Console can be INFO or DEBUG
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': [f'{APP_NAME}_file', 'console'], # Send Django logs to both file and console
            'level': 'DEBUG', # Set the minimum level for Django's internal logs
            'propagate': False, # Prevent logs from being passed to root logger
        },
        'django.request': { # Specific logger for HTTP requests (4xx, 5xx)
            'handlers': [f'{APP_NAME}_file', 'console'],
            'level': 'WARNING', # Keep at WARNING for HTTP request errors
            'propagate': False,
        },
        'django.channels': { # Logger for Channels-specific messages (like ASGI Debug)
            'handlers': [f'{APP_NAME}_file', 'console'],
            'level': 'DEBUG', # Set to DEBUG to see detailed Channels internal logs (like ASGI Debug)
            'propagate': False,
        },
        'django.db.backends': { # NEW: Logger for Django database queries
            'handlers': ['console'], # Only send to console for now, or to a separate DB log file
            'level': 'INFO', # Set to INFO or higher to suppress DEBUG SQL queries
            'propagate': False,
        },
        'django_q': { # NEW: Logger for Django-Q
            'handlers': ['q_file', 'console'], # Send Q logs to its own file and console
            'level': 'WARNING', # Set to WARNING to suppress frequent polling INFO messages
            'propagate': False, # Prevent logs from being passed to root logger
        },
        f'{APP_NAME}': { # Your custom app logger
            'handlers': [f'{APP_NAME}_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': { # Root logger catches anything not handled by specific loggers
        'handlers': ['console'], # Often just console for root
        'level': 'WARNING', # Catch unhandled warnings/errors by default
    },
}
