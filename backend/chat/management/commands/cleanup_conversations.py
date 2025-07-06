from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from chat.models import Conversation

class Command(BaseCommand):
    help = "Soft deletes conversations older than 30 days"

    def handle(self, *args, **options):
        threshold_date = timezone.now() - timedelta(days=30)
        old_conversations = Conversation.objects.filter(created_at__lt=threshold_date, deleted_at__isnull=True)

        count = old_conversations.update(deleted_at=timezone.now())
        self.stdout.write(self.style.SUCCESS(f"{count} old conversations soft-deleted."))
