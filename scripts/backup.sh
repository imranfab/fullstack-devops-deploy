#!/bin/bash
docker exec django_app python manage.py dumpdata > backup.json
