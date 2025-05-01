import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_invoice.settings')

# Initialize Celery
app = Celery('django_invoice')

# Load task modules from all registered Django app configs
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Debug task for development (only runs if DEBUG is True)
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    if settings.DEBUG:
        print(f'Request: {self.request!r}')