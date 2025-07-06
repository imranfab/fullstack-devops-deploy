from django.db.models.signals import post_save
from django.dispatch import receiver
from chat.models import Conversation, Message
from .models import UploadedFile, FileChunk
import mimetypes

import os
import fitz  # PyMuPDF
from docx import Document

@receiver(post_save, sender=UploadedFile)
def process_uploaded_file(sender, instance, created, **kwargs):
    
    if not instance.file or not hasattr(instance.file, "path"):
        return 
    
    if not created:
        return

    file_path = instance.file.path
    file_ext = os.path.splitext(file_path)[1].lower()

    text = ""

    if file_ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    elif file_ext == ".pdf":
        doc = fitz.open(file_path)
        text = "\n".join([page.get_text() for page in doc])

    elif file_ext == ".docx":
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])

    else:
        return  # Skip unsupported formats

    # Chunk and save
    chunk_size = 500
    for i in range(0, len(text), chunk_size):
        FileChunk.objects.create(
            file=instance,
            content=text[i:i+chunk_size],
            chunk_index=i // chunk_size
        )



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
