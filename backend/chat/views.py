from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import UploadedFile, Conversation, Message, Version
from .serializers import (
    UploadedFileSerializer, ConversationSerializer, MessageSerializer,
    TitleSerializer, VersionSerializer, ConversationSummarySerializer
)
from chat.utils.branching import make_branched_conversation
import hashlib
from django.utils import timezone

# -------------------------------
#  Basic Health Check
# -------------------------------
@api_view(["GET"])
def chat_root_view(request):
    return Response({"message": "Chat works!"})

# -------------------------------
# Conversation Endpoints
# -------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """List all active conversations for the authenticated user."""
    conversations = Conversation.objects.filter(
        user=request.user, deleted_at__isnull=True
    ).order_by("-modified_at")
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_conversations_branched(request):
    """Return conversations in branched structure."""
    conversations = Conversation.objects.filter(
        user=request.user, deleted_at__isnull=True
    ).order_by("-modified_at")

    data = ConversationSerializer(conversations, many=True).data
    for convo in data:
        make_branched_conversation(convo)

    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_conversation_branched(request, pk):
    """Return a single conversation in branched format."""
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=404)

    data = ConversationSerializer(conversation).data
    make_branched_conversation(data)
    return Response(data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_conversation(request):
    """Create a new conversation along with its messages."""
    try:
        conversation = Conversation.objects.create(
            title=request.data.get("title", "Mock title"),
            user=request.user
        )
        version = Version.objects.create(conversation=conversation)

        messages_data = request.data.get("messages", [])
        for idx, msg in enumerate(messages_data):
            serializer = MessageSerializer(data=msg)
            if serializer.is_valid():
                serializer.save(version=version)
                if idx == 0:
                    version.save()
            else:
                return Response(serializer.errors, status=400)

        conversation.active_version = version
        conversation.save()

        return Response(ConversationSerializer(conversation).data, status=201)
    except Exception as e:
        return Response({"detail": str(e)}, status=400)

@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def conversation_manage(request, pk):
    """Retrieve, update or hard-delete a conversation."""
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=404)

    if request.method == "GET":
        return Response(ConversationSerializer(conversation).data)

    if request.method == "PUT":
        serializer = ConversationSerializer(conversation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    if request.method == "DELETE":
        conversation.delete()
        return Response(status=204)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_change_title(request, pk):
    """Update the title of a conversation."""
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=404)

    serializer = TitleSerializer(data=request.data)
    if serializer.is_valid():
        conversation.title = serializer.validated_data["title"]
        conversation.save()
        return Response(status=204)
    return Response({"detail": "Invalid title"}, status=400)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_soft_delete(request, pk):
    """Soft delete a conversation by setting deleted_at."""
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
    except Conversation.DoesNotExist:
        return Response(status=404)

    conversation.deleted_at = timezone.now()
    conversation.save()
    return Response(status=204)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_conversation_summaries(request):
    """
    Return paginated conversation summaries with optional filtering by title.
    """
    # Get conversations for logged-in user, not deleted
    qs = Conversation.objects.filter(user=request.user, deleted_at__isnull=True).order_by("-modified_at")

    # Optional filtering by title query param
    title = request.query_params.get("title")
    if title:
        qs = qs.filter(title__icontains=title)

    # Paginate the queryset
    paginator = PageNumberPagination()
    paginated_qs = paginator.paginate_queryset(qs, request)
    serializer = ConversationSummarySerializer(paginated_qs, many=True)
    return paginator.get_paginated_response(serializer.data)
# -------------------------------
# Message & Version Endpoints
# -------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def conversation_add_message(request, pk):
    """Add a message to a conversation's active version."""
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
        version = conversation.active_version
    except Conversation.DoesNotExist:
        return Response(status=404)

    if not version:
        return Response({"detail": "Active version not set."}, status=400)

    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(version=version)
        return Response({
            "message": serializer.data,
            "conversation_id": conversation.id,
        }, status=201)
    return Response(serializer.errors, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def conversation_add_version(request, pk):
    """Fork a conversation starting from a specific root message."""
    try:
        conversation = Conversation.objects.get(user=request.user, pk=pk)
        version = conversation.active_version
        root_msg_id = request.data.get("root_message_id")
        root_message = Message.objects.get(pk=root_msg_id)
    except Conversation.DoesNotExist:
        return Response(status=404)
    except Message.DoesNotExist:
        return Response({"detail": "Root message not found"}, status=404)

    if root_message.version.conversation != conversation:
        return Response({"detail": "Invalid root message."}, status=400)

    new_version = Version.objects.create(
        conversation=conversation,
        parent_version=root_message.version,
        root_message=root_message
    )

    msgs = Message.objects.filter(version=version, created_at__lt=root_message.created_at)
    Message.objects.bulk_create([
        Message(content=m.content, role=m.role, version=new_version)
        for m in msgs
    ])

    conversation.active_version = new_version
    conversation.save()

    return Response(VersionSerializer(new_version).data, status=201)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def conversation_switch_version(request, pk, version_id):
    """Switch the active version of a conversation."""
    try:
        conversation = Conversation.objects.get(pk=pk)
        version = Version.objects.get(pk=version_id, conversation=conversation)
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=404)
    except Version.DoesNotExist:
        return Response({"detail": "Version not found"}, status=404)

    conversation.active_version = version
    conversation.save()
    return Response(status=204)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def version_add_message(request, pk):
    """Add a message to a specific version."""
    try:
        version = Version.objects.get(pk=pk)
    except Version.DoesNotExist:
        return Response(status=404)

    serializer = MessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(version=version)
        return Response({
            "message": serializer.data,
            "version_id": version.id,
        }, status=201)
    return Response(serializer.errors, status=400)

# -------------------------------
#  File Upload & Management
# -------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """Upload a file with duplication check via MD5."""
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=400)
    if file.size == 0:
        return Response({'error': 'File is empty'}, status=400)

    try:
        checksum = hashlib.md5(file.read()).hexdigest()
        if UploadedFile.objects.filter(checksum=checksum, user=request.user).exists():
            return Response({'error': 'File already uploaded'}, status=400)

        file.seek(0)
        uploaded = UploadedFile.objects.create(
            user=request.user,
            file=file,
            filename=file.name,
            checksum=checksum
        )
        return Response(UploadedFileSerializer(uploaded).data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_uploaded_files(request):
    """List uploaded files for the current user."""
    files = UploadedFile.objects.filter(user=request.user)
    return Response(UploadedFileSerializer(files, many=True).data)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_uploaded_file(request, pk):
    """Delete an uploaded file and its DB record."""
    try:
        file = UploadedFile.objects.get(pk=pk, user=request.user)
        file.file.delete(save=False)
        file.delete()
        return Response(status=204)
    except UploadedFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

