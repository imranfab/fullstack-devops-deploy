from django.core.management.base import BaseCommand
from chat.models import Role

class Command(BaseCommand):
    def handle(self, *args, **options):
        Role.objects.get_or_create(name="user")       # Create 'user' role if not exists
        Role.objects.get_or_create(name="assistant")  # Create 'assistant' role if not exists
        self.stdout.write(self.style.SUCCESS("Successfully created roles"))  # Success message
