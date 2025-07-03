from django.db.models.signals import post_save
from django.dispatch import receiver
from chat.models import Conversation, Message

@receiver(post_save, sender=Message)
def generate_conversation_summary(sender, instance, created, **kwargs):
    if not created:
        return

    conversation = instance.version.conversation

    # Get all messages in the conversation
    messages = Message.objects.filter(version__conversation=conversation).order_by("created_at")

    # Create a simple summary by joining the first few message contents
    summary = " ".join([msg.content[:50] for msg in messages[:5]])

    # Save the summary to the conversation
    conversation.summary = summary
    conversation.save()
