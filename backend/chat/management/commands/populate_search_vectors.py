from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from chat.models import FileChunk

class Command(BaseCommand):
    help = "Populate search_vector field in FileChunk"

    def handle(self, *args, **kwargs):
        chunks = FileChunk.objects.all()
        count = 0

        for chunk in chunks:
            chunk.search_vector = SearchVector('content')
            chunk.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {count} FileChunks with search_vector"))
