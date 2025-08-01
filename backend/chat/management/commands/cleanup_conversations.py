# chat/management/commands/cleanup_conversations.py

from django.core.management.base import BaseCommand
from chat.models import Conversation
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Deletes conversations older than 30 days'  # Command description

    def handle(self, *args, **kwargs):
        threshold = timezone.now() - timedelta(days=30)  # Cutoff date
        deleted, _ = Conversation.objects.filter(created_at__lt=threshold).delete()  # Delete old conversations
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old conversations"))  # Print result
