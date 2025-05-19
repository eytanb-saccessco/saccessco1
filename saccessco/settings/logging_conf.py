# logging_conf.py

import os
from pathlib import Path

# Define the log directory and ensure it exists.
APP_NAME = "saccessco"
LOG_DIR = Path(f"/var/log/{APP_NAME}")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # Keep Django's default loggers.
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
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': [f'{APP_NAME}_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        f'{APP_NAME}': {
            'handlers': [f'{APP_NAME}_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
