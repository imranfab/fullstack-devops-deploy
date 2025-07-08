from celery import shared_task
from django.utils import timezone
from chat.models import Conversation
from datetime import timedelta

@shared_task
def cleanup_old_conversations():
    cutoff = timezone.now() - timedelta(days=30)
    deleted = Conversation.objects.filter(created_at__lt=cutoff, deleted_at__isnull=True).update(deleted_at=timezone.now())
    return f"{deleted} conversations soft-deleted."