import uuid

from django.db import models

from authentication.models import CustomUser

from .utils.summarizer import generate_conversation_summary
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.core.exceptions import ValidationError

class FileChunk(models.Model):
    file = models.ForeignKey(
        "UploadedFile",
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    content = models.TextField()
    chunk_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"]),
        ]
        ordering = ["chunk_index"]  

    def __str__(self):
        return f"Chunk {self.chunk_index} of File ID {self.file_id}: {self.content[:60]}..."


class UploadedFile(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_hash = models.CharField(max_length=64, unique=True)
    conversation = models.ForeignKey(
        "Conversation", 
        on_delete=models.CASCADE,
        related_name="files",
        null=True,
        blank=True
    )
    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.file.name
    
    def clean(self):
        if not self.file:
            raise ValidationError("File cannot be empty.")


class Role(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, blank=False, null=False, default="Mock title")
    topic = models.CharField(max_length=100, null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version", null=True, blank=True, on_delete=models.CASCADE, related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField()
    summary = models.TextField(blank=True, null=True) 
    
    def save(self, *args, **kwargs):
        if self.text and not self.summary:
            self.summary = generate_conversation_summary(self.text)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def version_count(self):
        return self.versions.count()

    version_count.short_description = "Number of versions"


class Version(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey("Conversation", related_name="versions", on_delete=models.CASCADE)
    parent_version = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    root_message = models.ForeignKey(
        "Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="root_message_versions"
    )

    def __str__(self):
        if self.root_message:
            return f"Version of `{self.conversation.title}` created at `{self.root_message.created_at}`"
        else:
            return f"Version of `{self.conversation.title}` with no root message yet"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField(blank=False, null=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.ForeignKey("Version", related_name="messages", on_delete=models.CASCADE)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.version.conversation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."
