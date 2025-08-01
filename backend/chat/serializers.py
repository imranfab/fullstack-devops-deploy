from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from chat.models import Conversation, Message, Role, Version
from .models import Conversation, UploadedFile


def should_serialize(validated_data, field_name) -> bool:
    """
    Helper function to check if a field should be serialized,
    i.e., if the field exists and is not None in validated_data.
    """
    if validated_data.get(field_name) is not None:
        return True


class TitleSerializer(serializers.Serializer):
    """
    Simple serializer for validating/updating a title string.
    Used when only a title update is needed.
    """
    title = serializers.CharField(max_length=100, required=True)


class VersionTimeIdSerializer(serializers.Serializer):
    """
    Serializer that exposes only version id and created_at datetime.
    Useful for listing versions in minimal form.
    """
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model.
    Role is represented by its 'name' string instead of primary key.
    """
    role = serializers.SlugRelatedField(slug_field="name", queryset=Role.objects.all())

    class Meta:
        model = Message
        fields = [
            "id",          # Primary key
            "content",     # Message text content
            "role",        # Role name (e.g. user, assistant)
            "created_at",  # Timestamp, read-only
        ]
        read_only_fields = ["id", "created_at", "version"]  # version is set automatically

    def create(self, validated_data):
        """
        Create a new Message instance.
        """
        message = Message.objects.create(**validated_data)
        return message

    def to_representation(self, instance):
        """
        Customize output representation.
        Adds an empty "versions" list to each message (potentially for frontend use).
        """
        representation = super().to_representation(instance)
        representation["versions"] = []  # placeholder for versions data if needed
        return representation


class VersionSerializer(serializers.ModelSerializer):
    """
    Serializer for Version model, including nested messages.
    Adds 'active' boolean field indicating if this version is the active version in the conversation.
    """
    messages = MessageSerializer(many=True)  # nested serializer for messages
    active = serializers.SerializerMethodField()  # computed field
    conversation_id = serializers.UUIDField(source="conversation.id")  # expose conversation id
    created_at = serializers.SerializerMethodField()  # custom created_at field logic

    class Meta:
        model = Version
        fields = [
            "id",
            "conversation_id",  # UUID of the parent conversation
            "root_message",
            "messages",        # nested messages data
            "active",          # is this version the active one?
            "created_at",      # read-only, custom computed field
            "parent_version",  # optional, allows branching
        ]
        read_only_fields = ["id", "conversation"]

    @staticmethod
    def get_active(obj):
        """
        Returns True if this version is the active version for the conversation.
        """
        return obj == obj.conversation.active_version

    @staticmethod
    def get_created_at(obj):
        """
        Returns the timestamp for the version creation.
        Uses root_message's creation time if set, else falls back to conversation creation time.
        """
        if obj.root_message is None:
            return timezone.localtime(obj.conversation.created_at)
        return timezone.localtime(obj.root_message.created_at)

    def create(self, validated_data):
        """
        Creates a Version along with nested messages.
        """
        messages_data = validated_data.pop("messages")
        version = Version.objects.create(**validated_data)
        for message_data in messages_data:
            Message.objects.create(version=version, **message_data)

        return version

    def update(self, instance, validated_data):
        """
        Updates Version fields and nested messages.
        Requires at least one of 'conversation', 'parent_version', or 'root_message' fields to be provided.
        """
        instance.conversation = validated_data.get("conversation", instance.conversation)
        instance.parent_version = validated_data.get("parent_version", instance.parent_version)
        instance.root_message = validated_data.get("root_message", instance.root_message)

        # Validate that at least one required field is provided
        if not any(
            [
                should_serialize(validated_data, "conversation"),
                should_serialize(validated_data, "parent_version"),
                should_serialize(validated_data, "root_message"),
            ]
        ):
            raise ValidationError(
                "At least one of the following fields must be provided: conversation, parent_version, root_message"
            )
        instance.save()

        # Update or create nested messages
        messages_data = validated_data.pop("messages", [])
        for message_data in messages_data:
            if "id" in message_data:
                # Update existing message
                message = Message.objects.get(id=message_data["id"], version=instance)
                message.content = message_data.get("content", message.content)
                message.role = message_data.get("role", message.role)
                message.save()
            else:
                # Create new message
                Message.objects.create(version=instance, **message_data)

        return instance


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model including nested versions.
    """
    versions = VersionSerializer(many=True)

    class Meta:
        model = Conversation
        fields = [
            "id",             # UUID primary key
            "title",          # Conversation title
            "active_version", # ForeignKey to active version (UUID)
            "versions",       # Nested list of versions
            "modified_at",    # Timestamp, read-only
        ]

    def create(self, validated_data):
        """
        Creates a Conversation and nested versions.
        """
        versions_data = validated_data.pop("versions", [])
        conversation = Conversation.objects.create(**validated_data)
        for version_data in versions_data:
            version_serializer = VersionSerializer(data=version_data)
            if version_serializer.is_valid():
                version_serializer.save(conversation=conversation)

        return conversation

    def update(self, instance, validated_data):
        """
        Updates Conversation fields and nested versions.
        Also updates active_version by its UUID.
        """
        instance.title = validated_data.get("title", instance.title)
        active_version_id = validated_data.get("active_version", instance.active_version)
        if active_version_id is not None:
            active_version = Version.objects.get(id=active_version_id)
            instance.active_version = active_version
        instance.save()

        # Update or create nested versions
        versions_data = validated_data.pop("versions", [])
        for version_data in versions_data:
            if "id" in version_data:
                version = Version.objects.get(id=version_data["id"], conversation=instance)
                version_serializer = VersionSerializer(version, data=version_data)
            else:
                version_serializer = VersionSerializer(data=version_data)
            if version_serializer.is_valid():
                version_serializer.save(conversation=instance)

        return instance


class ConversationSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for returning conversation summaries.
    Only returns id, title, and summary text.
    """
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'summary']


class UploadedFileSerializer(serializers.ModelSerializer):
    """
    Serializer for uploaded files.
    Returns metadata like filename, checksum, and upload timestamp.
    """
    class Meta:
        model = UploadedFile
        fields = ['id', 'file', 'uploaded_at', 'filename', 'checksum']
