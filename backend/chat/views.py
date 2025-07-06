from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from chat.models import Conversation, Message, Version, UploadedFile
from chat.serializers import ConversationSerializer, MessageSerializer, TitleSerializer, VersionSerializer,UploadedFileSerializer
from chat.utils.branching import make_branched_conversation
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import ListAPIView
from .models import UploadedFile ,FileChunk
from .serializers import UploadedFileSerializer
from chat.utils.summarizer import generate_conversation_summary
from rest_framework.filters import SearchFilter, OrderingFilter
import hashlib
from rest_framework.generics import DestroyAPIView
from django.db import IntegrityError
import os
import fitz 
import docx
import google.generativeai as genai
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
# from chat.utils.rag import generate_rag_answer 
from chat.permissions import require_roles

from .utils.file_processing import split_into_chunks

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
import logging
logger = logging.getLogger('file_activity')


@api_view(["POST"])
def generate_summary_api(request, pk):
    cache_key = f"conversation_summary_{pk}"
    cached_summary = cache.get(cache_key)

    if cached_summary:
        return Response({
            "message": "Summary from cache",
            "summary": cached_summary
        })

    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=404)

    summary = generate_conversation_summary(conversation)

    conversation.summary = summary
    conversation.save()

    cache.set(cache_key, summary, timeout=60 * 60)  # Cache for 1 hour

    return Response({
        "message": "Summary generated",
        "summary": summary
    })

class IsUploaderOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role in ['admin', 'uploader']

class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsAdminOnly])
def delete_file(request, pk):
    try:
        file = UploadedFile.objects.get(pk=pk)
        file.delete()
        logger.info(f"User {request.user} deleted file {file.file.name}")
        return Response({"message": "File deleted successfully"})
    except UploadedFile.DoesNotExist:
        return Response({"error": "File not found"}, status=404)

class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'

class FileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsUploaderOrAdmin]

    def extract_text_from_file(self, uploaded_file):
        try:
            file_path = uploaded_file.file.path
            chunks = []

            if file_path.endswith(".pdf"):
                doc = fitz.open(file_path)
                for page in doc:
                    text = page.get_text()
                    if text.strip():
                        chunks.append(text.strip())

            elif file_path.endswith(".docx"):
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
                if text.strip():
                    chunks.append(text.strip())

            else:
            # Default to reading as plain text
                if not file_content:
                    return Response({"error": "Uploaded file is empty."}, status=400)
                
                file_content = uploaded_file.read().decode('utf-8', errors='ignore')
                chunks = split_into_chunks(file_content)
                uploaded_file.seek(0)

            return chunks
        except Exception as e:
        # Likely triggered during tests or in-memory file
            try:
                raw_text = uploaded_file.file.read().decode("utf-8", errors="ignore")
                return [raw_text]
            except Exception as inner_e:
                logger.error(f"Failed to extract text from file: {inner_e}")
                return []

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"error": "File is required."}, status=400)
        
        logger.info(f"User {request.user} uploaded file {uploaded_file.name}")
        conversation_id = request.data.get("conversation")
        if not conversation_id:
            return Response({"error": "Conversation ID is required."}, status=400)

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found."}, status=404)

        file_content = uploaded_file.read()
        logger.info(f"File size: {len(file_content)} bytes")
        
        if not file_content:
            return Response({"error": "Uploaded file is empty."}, status=400)
        
        file_hash = hashlib.sha256(file_content).hexdigest()
        uploaded_file.seek(0)

        if UploadedFile.objects.filter(file_hash=file_hash).exists():
            logger.warning(f"Duplicate file upload attempt by user {request.user}: {uploaded_file.name}")
            return Response({"error": "Duplicate file already exists."}, status=400)
        # Save UploadedFile instance
        
        
        data = request.data.copy()
        data["file"] = uploaded_file
        data["conversation"] = conversation.id
        data["file_hash"] = file_hash

        serializer = UploadedFileSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            
            try:
                file_instance = serializer.save()
            except IntegrityError:
                return Response({"error": "Duplicate file detected."}, status=400)

            # file_instance.file.open()
            
            try:
                chunks = self.extract_text_from_file(file_instance)
                for i, chunk in enumerate(chunks):
                    FileChunk.objects.create(
                        uploaded_file=file_instance,
                        content=chunk,
                        chunk_index=i
                    )
            except Exception as e:
                logger.error(f"Text extraction failed: {e}")
                return Response({"error": "File processing failed."}, status=500)
            

            logger.info(f"User {request.user} uploaded file {uploaded_file.name}")
            return Response(
                {"message": "File uploaded successfully", "data": serializer.data},
                status=201
            )

        logger.warning(f"File upload failed for user {request.user}: {serializer.errors}")
        return Response(serializer.errors, status=400)


# @api_view(["POST"])
# # @permission_classes([IsAuthenticated])
# def generate_answer(request, pk):
#     query = request.data.get("query", "")
#     if not query:
#         return Response({"error": "Query is required."}, status=400)

#     conversation = get_object_or_404(Conversation, pk=pk, user=request.user)

#     answer = generate_rag_answer(conversation, query)
#     return Response({"answer": answer})




@api_view(["POST"])
def rag_answer(request):
    query = request.data.get("query", "")
    if not query:
        return Response({"error": "Query is required."}, status=400)

    matching_chunks = FileChunk.objects.filter(content__icontains=query)[:5]

    if not matching_chunks:
        return Response({"answer": "No relevant content found in uploaded files."})

    context = "\n\n".join(chunk.content for chunk in matching_chunks)

    prompt = f"Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer:"
    try:
        response = model.generate_content(prompt)
        return Response({"answer": response.text})
    except Exception as e:
        return Response({"error": f"Gemini API error: {str(e)}"}, status=500)


class FileDeleteView(DestroyAPIView):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    permission_classes = [IsAuthenticated, IsUploaderOrAdmin]
    lookup_field = 'pk'
    
    def perform_destroy(self, instance):
        logger.info(f"User {self.request.user} deleted file {instance.file.name}")
        instance.delete()

class ConversationSummaryListView(ListAPIView):
    queryset = Conversation.objects.exclude(summary__isnull=True).exclude(summary__exact="").order_by('-modified_at')
    serializer_class = ConversationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'summary']  
    ordering_fields = ['created_at', 'modified_at']
    ordering = ['-modified_at']


@api_view(["POST"])
def generate_summary_api(request, pk):
    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=404)

    summary = generate_conversation_summary(conversation)
    conversation.summary = summary
    conversation.save()

    return Response({"message": "Summary generated", "summary": summary})

@api_view(["GET"])
def get_conversation_files(request, pk):
    try:
        conversation = Conversation.objects.get(pk=pk)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=404)

    files = UploadedFile.objects.filter(conversation=conversation)
    serialized = UploadedFileSerializer(files, many=True)
    return Response(serialized.data)


class FileListView(ListAPIView):
    queryset = UploadedFile.objects.all().order_by("-uploaded_at")
    serializer_class = UploadedFileSerializer


@api_view(["GET"])
def chat_root_view(request):
    return Response({"message": "Chat works!"}, status=status.HTTP_200_OK)


@permission_classes([IsAuthenticated])
@api_view(["GET"])
def get_conversations(request):
    conversations = Conversation.objects.filter(user=request.user, deleted_at__isnull=True).order_by("-modified_at")
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@permission_classes([IsAuthenticated])
@api_view(["GET"])
def get_conversations_branched(request):
    conversations = Conversation.objects.filter(user=request.user, deleted_at__isnull=True).order_by("-modified_at")
    conversations_serializer = ConversationSerializer(conversations, many=True)
    conversations_data = conversations_serializer.data

    for conversation_data in conversations_data:
        make_branched_conversation(conversation_data)

    return Response(conversations_data, status=status.HTTP_200_OK)


@permission_classes([IsAuthenticated])
@api_view(["GET"])
def get_conversation_branched(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

    conversation_serializer = ConversationSerializer(conversation)
    conversation_data = conversation_serializer.data
    make_branched_conversation(conversation_data)

    return Response(conversation_data, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_conversation(request):
    title = request.data.get("title", "")
    messages_data = request.data.get("messages", [])

    try:
        
        conversation = Conversation.objects.create(user=request.user, title=title)        
        version = Version.objects.create(conversation=conversation)
        
        for idx, message_data in enumerate(messages_data):
            message_serializer = MessageSerializer(data=message_data)
            if message_serializer.is_valid():
                message_serializer.save(version=version)
            else:
                return Response(message_serializer.errors, status=400)
        
        conversation.active_version = version
        conversation.save()

        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=201)

    except Exception as e:
        return Response({"detail": str(e)}, status=400)


@permission_classes([IsAuthenticated])
@api_view(["GET", "PUT", "DELETE"])
def conversation_manage(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        # serializer = ConversationSerializer(conversation)
        serializer = ConversationSerializer(conversation, context={"request": request})
        return Response(serializer.data)

    elif request.method == "PUT":
        serializer = ConversationSerializer(conversation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@permission_classes([IsAuthenticated])
@api_view(["PUT"])
def conversation_change_title(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = TitleSerializer(data=request.data)

    if serializer.is_valid():
        conversation.title = serializer.data.get("title")
        conversation.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response({"detail": "Title not provided"}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticated])
@api_view(["PUT"])
def conversation_soft_delete(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    conversation.deleted_at = timezone.now()
    conversation.save()
    return Response(status=status.HTTP_204_NO_CONTENT)


@permission_classes([IsAuthenticated])
@api_view(["POST"])
def conversation_add_message(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
        version = conversation.active_version
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if version is None:
        return Response({"detail": "Active version not set for this conversation."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(version=version)
        # return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            {
                "message": serializer.data,
                "conversation_id": conversation.id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticated])
@api_view(["POST"])
def conversation_add_version(request, pk):
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
        version = conversation.active_version
        root_message_id = request.data.get("root_message_id")
        root_message = Message.objects.get(pk=root_message_id)
    except Conversation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except Message.DoesNotExist:
        return Response({"detail": "Root message not found"}, status=status.HTTP_404_NOT_FOUND)

    # Check if root message belongs to the same conversation
    if root_message.version.conversation != conversation:
        return Response({"detail": "Root message not part of the conversation"}, status=status.HTTP_400_BAD_REQUEST)

    new_version = Version.objects.create(
        conversation=conversation, parent_version=root_message.version, root_message=root_message
    )

    # Copy messages before root_message to new_version
    messages_before_root = Message.objects.filter(version=version, created_at__lt=root_message.created_at)
    new_messages = [
        Message(content=message.content, role=message.role, version=new_version) for message in messages_before_root
    ]
    Message.objects.bulk_create(new_messages)

    # Set the new version as the current version
    conversation.active_version = new_version
    conversation.save()

    serializer = VersionSerializer(new_version)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@permission_classes([IsAuthenticated])
@api_view(["PUT"])
def conversation_switch_version(request, pk, version_id):
    try:
        conversation = Conversation.objects.get(pk=pk)
        version = Version.objects.get(pk=version_id, conversation=conversation)
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
    except Version.DoesNotExist:
        return Response({"detail": "Version not found"}, status=status.HTTP_404_NOT_FOUND)

    conversation.active_version = version
    conversation.save()

    return Response(status=status.HTTP_204_NO_CONTENT)


@permission_classes([IsAuthenticated])
@api_view(["POST"])
def version_add_message(request, pk):
    try:
        version = Version.objects.get(pk=pk)
    except Version.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(version=version)
        return Response(
            {
                "message": serializer.data,
                "version_id": version.id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
