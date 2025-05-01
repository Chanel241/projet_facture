"""
WSGI configuration for the django_invoice project.

This file exposes the WSGI callable as a module-level variable named `application`.

For more information, see:
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Set the default Django settings module for the WSGI application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_invoice.settings')

# Initialize the WSGI application
application = get_wsgi_application()