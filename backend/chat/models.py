import uuid
from django.db import models
from authentication.models import CustomUser
from chat.utils.summarizer import generate_summary  # Your own T5-based summarizer


class Role(models.Model):
    """
    Represents the role of a message sender, e.g., "user", "assistant".
    """
    name = models.CharField(max_length=20, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    """
    Stores chat conversations tied to a user.
    Supports soft deletion with deleted_at and keeps track of an active version.
    Also stores a summary of the conversation content.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, default="Mock title")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)  # Soft delete timestamp
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    summary = models.TextField(blank=True, null=True)  # Summary generated from messages

    def __str__(self):
        return self.title

    def version_count(self):
        """
        Returns the total number of versions under this conversation.
        Useful for admin or UI display.
        """
        return self.versions.count()
    version_count.short_description = "Number of versions"

    def update_summary(self):
        """
        Generate and update the summary field by concatenating all messages content
        in this conversation and passing it to your summarizer utility.
        Called automatically after a message is saved.
        """
        from .models import Message  # Avoid circular import

        messages = Message.objects.filter(version__conversation=self).order_by("created_at")
        combined_text = " ".join(msg.content for msg in messages)
        if combined_text.strip():
            self.summary = generate_summary(combined_text)
            self.save()


class Version(models.Model):
    """
    Represents a specific version (or branch) of a conversation.
    Versions can be branched from parent versions and link to a root message.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey("Conversation", related_name="versions", on_delete=models.CASCADE)
    parent_version = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    root_message = models.ForeignKey(
        "Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="root_message_versions"
    )

    def __str__(self):
        return f"Version of `{self.conversation.title}`"


class Message(models.Model):
    """
    Individual chat messages belonging to a specific version.
    Each message has a role (e.g., user or assistant).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.ForeignKey("Version", related_name="messages", on_delete=models.CASCADE)

    class Meta:
        ordering = ["created_at"]  # Ensures messages are retrieved in creation order

    def save(self, *args, **kwargs):
        """
        Override save to automatically update the conversation summary
        whenever a new message is saved.
        """
        super().save(*args, **kwargs)
        self.version.conversation.update_summary()

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."  # Display role and snippet of content


class UploadedFile(models.Model):
    """
    Tracks files uploaded by users.
    Stores file metadata like filename, checksum, size, and upload timestamp.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    checksum = models.CharField(max_length=255, unique=True)  # For detecting duplicates
    size = models.IntegerField(null=True, blank=True)  # File size in bytes

    def save(self, *args, **kwargs):
        # Automatically sets size if not already set
        if not self.size and self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return self.filename
