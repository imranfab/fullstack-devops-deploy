import logging
import os
from django.core.files.storage import FileSystemStorage
from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import google.generativeai as genai

from chat.utils.summarizer import generate_summary
from chat.models import Message
from .utils import process_file
from .permissions import HasRolePermission

logger = logging.getLogger(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Health check endpoint
@api_view(["GET"])
def gemini_root_view(request):
    return JsonResponse({"message": "Gemini endpoint works!"})


# Generate title from user question and chatbot response
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_title(request):
    try:
        user_q = request.data.get("user_question")
        bot_res = request.data.get("chatbot_response")
        if not user_q or not bot_res:
            return Response({"error": "Missing user_question or chatbot_response."}, status=400)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Generate a title for the following conversation: {user_q} {bot_res}"
        response = model.generate_content(prompt)
        return JsonResponse({"content": response.text})
    except Exception as e:
        logger.exception("Error generating title")
        return Response({"error": "Failed to generate title."}, status=500)


# Simple Gemini prompt/response
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_answer(request):
    try:
        prompt = request.data.get("user_question")
        if not prompt:
            return Response({"error": "Missing user_question."}, status=400)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, stream=True)

        def stream_response():
            for chunk in response:
                yield chunk.text

        return StreamingHttpResponse(stream_response(), content_type="text/html")
    except Exception as e:
        logger.exception("Error generating answer")
        return Response({"error": "Failed to generate answer."}, status=500)


# Handle full conversation context with Gemini
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_conversation(request):
    try:
        conversation = request.data.get("conversation")
        if not conversation:
            return Response({"error": "Missing conversation."}, status=400)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "\n".join(conversation)
        response = model.generate_content(prompt, stream=True)

        def stream_response():
            for chunk in response:
                yield chunk.text

        return StreamingHttpResponse(stream_response(), content_type="text/html")
    except Exception as e:
        logger.exception("Error generating conversation answer")
        return Response({"error": "Failed to generate conversation answer."}, status=500)


# Dummy document retriever (to be replaced)
def retrieve_documents(query):
    return ["Document content related to query..."]


# Dummy response generator using retrieved docs
def generate_response(query, context):
    return f"Answer based on '{query}' with context."


# RAG: combine retrieval + Gemini answer
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_generate(request):
    query = request.data.get('query')
    if not query:
        return Response({"error": "Query is required."}, status=400)
    try:
        docs = retrieve_documents(query)
        context = " ".join(docs)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"{query} {context}"
        response = model.generate_content(prompt)
        return Response({
            "query": query,
            "answer": response.text,
            "retrieved_documents": docs,
        })
    except Exception as e:
        logger.exception("RAG generation failed")
        return Response({"error": "Failed to generate RAG answer."}, status=500)


# Basic file upload without permission check
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def file_upload(request):
    file = request.FILES.get('file')
    if not file:
        return Response({"error": "File is required."}, status=400)
    try:
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_url = fs.url(filename)
        process_file(file_url)
        logger.info(f"File uploaded: {file.name}")
        return Response({"file_url": file_url})
    except Exception as e:
        logger.exception("File upload failed")
        return Response({"error": "Failed to upload file."}, status=500)


# Secure file upload (requires role permission)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasRolePermission])
def file_upload_with_role_permission(request):
    file = request.FILES.get('file')
    if not file:
        return Response({"error": "File is required."}, status=400)
    try:
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_url = fs.url(filename)
        process_file(file_url)
        logger.info(f"File uploaded with permission: {file.name}")
        return Response({"file_url": file_url})
    except Exception as e:
        logger.exception("File upload with permission failed")
        return Response({"error": "Failed to upload file."}, status=500)

file_upload_with_role_permission.permission_name = "file_upload"


# Dummy file access (with role permission)
@api_view(['GET'])
@permission_classes([IsAuthenticated, HasRolePermission])
def file_access(request):
    try:
        logger.info(f"Files accessed by user: {request.user}")
        return Response({"message": "Files accessed"})
    except Exception as e:
        logger.exception("File access failed")
        return Response({"error": "Failed to access files."}, status=500)

file_access.permission_name = "file_access"


# Delete uploaded file by name
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, HasRolePermission])
def file_delete(request):
    file_name = request.data.get("filename")
    if not file_name:
        return Response({"error": "Filename required."}, status=400)
    fs = FileSystemStorage()
    try:
        fs.delete(file_name)
        logger.info(f"File deleted: {file_name}")
        return Response({"message": f"{file_name} deleted."})
    except Exception as e:
        logger.exception("File deletion failed")
        return Response({"error": "Failed to delete file."}, status=500)

file_delete.permission_name = "file_delete"


# Summarize conversation messages by conversation_id
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_summary(request):
    conversation_id = request.GET.get('conversation_id')
    if not conversation_id:
        return Response({"error": "conversation_id is required"}, status=400)
    try:
        summary = cache.get(conversation_id)
        if summary is None:
            messages = Message.objects.filter(
                version__conversation_id=conversation_id
            ).order_by("created_at")
            if not messages.exists():
                return Response({"error": "No messages found."}, status=404)
            full_text = " ".join(msg.content for msg in messages)
            summary = generate_summary(full_text)
            cache.set(conversation_id, summary, timeout=60 * 15)
        return Response({"summary": summary})
    except Exception as e:
        logger.exception("Summary generation failed")
        return Response({"error": "Failed to generate summary."}, status=500)
