"""
ASGI configuration for the django_invoice project.

This file exposes the ASGI callable as a module-level variable named `application`.

For more information, see:
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Set the default Django settings module for the ASGI application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_invoice.settings')

# Initialize the ASGI application
application = get_asgi_application()