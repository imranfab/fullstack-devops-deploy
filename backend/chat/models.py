import uuid

from django.db import models

from authentication.models import CustomUser


class Role(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # <-- Added default=uuid.uuid4
    title = models.CharField(max_length=100, blank=False, null=False, default="Mock title")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version", null=True, blank=True, on_delete=models.CASCADE, related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def version_count(self):
        return self.versions.count()

    version_count.short_description = "Number of versions"

    def generate_summary(self):
        messages = []
        if self.active_version:
            messages = self.active_version.messages.all()[:3]  # ⬅️ Limit to first 3 directly in query
        else:
            messages = Message.objects.filter(version__conversation=self).order_by("created_at")[:3]  # ⬅️ Better fallback

        contents = [msg.content for msg in messages]
        return " | ".join(contents) if contents else "No messages yet"



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
        is_new = self._state.adding  # check if this is a new message
        super().save(*args, **kwargs)  # first, save the message normally

        if is_new:
            conversation = self.version.conversation
            conversation.summary = conversation.generate_summary()
            conversation.save()

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."
