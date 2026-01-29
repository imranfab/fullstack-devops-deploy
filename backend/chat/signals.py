from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message
import openai

@receiver(post_save, sender=Message)
def generate_summary(sender, instance, created, **kwargs):
    if not created:
        return

    # Message → Version → Conversation
    conversation = instance.version.conversation

    messages = Message.objects.filter(
        version__conversation=conversation
    ).order_by("created_at")

    text = "\n".join(msg.content for msg in messages)

    if not text.strip():
        return

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Summarize this conversation briefly."},
                {"role": "user", "content": text[:3000]}
            ]
        )
        summary = response.choices[0].message.content.strip()

    except Exception:
        summary = "Summary generation failed."

    conversation.summary = summary
    conversation.save(update_fields=["summary"])
