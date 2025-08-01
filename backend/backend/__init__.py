from __future__ import absolute_import, unicode_literals
# Ensures compatibility between Python 2 and 3 for import behavior and string literals

from .celery import app as celery_app
# Imports the Celery app instance from celery.py and exposes it as celery_app

__all__ = ('celery_app',)
# Defines the public API of this module to include celery_app
