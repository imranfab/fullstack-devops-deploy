import uuid

from django.db import models

from authentication.models import CustomUser
#Imported generate summary function
from src.utils.gpt import generate_summary 


class Role(models.Model):
    name = models.CharField(max_length=20, blank=False, null=False, default="user")

    def __str__(self):
        return self.name


class Conversation(models.Model):
    content = models.TextField(default="Placeholder content") #Addede default value
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, blank=False, null=False, default="Mock title")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active_version = models.ForeignKey(
        "Version", null=True, blank=True, on_delete=models.CASCADE, related_name="current_version_conversations"
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    # New field for conversation summary
    summary = models.TextField(null=True, blank=True, default="")  # New summary field
    
    # def save(self, *args, **kwargs):
    #     if self.content and not self.summary:
    #         self.summary = generate_summary(self.content)
    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        #if not self.summary and self.messages:
        if not self.summary and Message.objects.filter(version__conversation=self).exists():
            try:
                messages = Message.objects.filter(version__conversation=self).order_by("created_at")
                message_list = [{"role": message.role.name, "content": message.content} for message in messages]
                self.summary = generate_summary(message_list, model="gpt4")
            except Exception as e:
                print(f"Summary generation failed: {e}")
                self.summary = "Summary generation failed."
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
    #Changed this as per chatgpt
    content = models.TextField() #blank=False, null=False
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    #conversation = models.ForeignKey(Conversation,related_name = "messages",on_delete=models.CASCADE)
    conversation = models.ForeignKey("Conversation",on_delete=models.CASCADE,null=True,blank=True)
    version = models.ForeignKey("Version", related_name="messages", on_delete=models.CASCADE)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.version.conversation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."
