import uuid
from django.db import models
from authentication.models import CustomUser
from chat.utils.summarizer import generate_summary  # Your own T5-based summarizer


class Role(models.Model):
    name = models.CharField(max_length=20, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, default="Mock title")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version", null=True, blank=True, on_delete=models.CASCADE, related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    summary = models.TextField(blank=True, null=True)  # ✅ Summary field

    def __str__(self):
        return self.title

    def version_count(self):
        return self.versions.count()

    version_count.short_description = "Number of versions"

    def update_summary(self):
        from .models import Message  # Avoid circular import
        messages = Message.objects.filter(version__conversation=self).order_by("created_at")
        combined_text = " ".join(msg.content for msg in messages)
        if combined_text.strip():
            self.summary = generate_summary(combined_text)
            self.save()


class Version(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey("Conversation", related_name="versions", on_delete=models.CASCADE)
    parent_version = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    root_message = models.ForeignKey(
        "Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="root_message_versions"
    )

    def __str__(self):
        return f"Version of `{self.conversation.title}`"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.ForeignKey("Version", related_name="messages", on_delete=models.CASCADE)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.version.conversation.update_summary()  # ✅ Auto-trigger on message save

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."
