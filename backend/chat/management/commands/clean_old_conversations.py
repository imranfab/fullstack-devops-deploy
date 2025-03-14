from django.core.management.base import BaseCommand
from django.utils.timezone import now
from chat.models import Conversation
import datetime

class Command(BaseCommand):
    help = "Deletes soft-deleted conversations older than 30 days."

    def handle(self, *args, **kwargs):
        threshold_date = now() - datetime.timedelta(days=30)
        old_conversations = Conversation.objects.filter(deleted_at__lte=threshold_date)

        count = old_conversations.count()
        old_conversations.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {count} old conversations."))
