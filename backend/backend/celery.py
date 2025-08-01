import os
from celery import Celery

# Set default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Create a new Celery app instance named 'backend'
app = Celery('backend')

# Load task modules from Django settings, using the CELERY namespace for config keys
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks.py in installed apps
app.autodiscover_tasks()
