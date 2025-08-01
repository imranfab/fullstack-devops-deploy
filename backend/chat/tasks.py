from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from chat.models import Conversation

@shared_task
def cleanup_old_conversations():
    # Set cutoff date 30 days ago
    threshold_date = timezone.now() - timedelta(days=30)
    
    # Delete conversations older than cutoff
    deleted_count, _ = Conversation.objects.filter(created_at__lt=threshold_date).delete()
    
    # Return number of deleted conversations
    return f"Deleted {deleted_count} old conversations"
