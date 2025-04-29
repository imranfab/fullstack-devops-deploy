from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from chat.models import Conversation, Message, Role, Version


def should_serialize(validated_data, field_name) -> bool:
    return validated_data.get(field_name) is not None


class TitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, required=True)


class VersionTimeIdSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()


class MessageSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(slug_field="name", queryset=Role.objects.all())

    class Meta:
        model = Message
        fields = ["id", "content", "role", "created_at"]
        read_only_fields = ["id", "created_at", "version"]

    def create(self, validated_data):
        return Message.objects.create(**validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation


class VersionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True)
    active = serializers.SerializerMethodField()
    conversation_id = serializers.UUIDField(source="conversation.id")
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Version
        fields = [
            "id",
            "conversation_id",
            "root_message",
            "messages",
            "active",
            "created_at",
            "parent_version",
        ]
        read_only_fields = ["id", "conversation"]

    @staticmethod
    def get_active(obj):
        return obj == obj.conversation.active_version

    @staticmethod
    def get_created_at(obj):
        if obj.root_message is None:
            return timezone.localtime(obj.conversation.created_at)
        return timezone.localtime(obj.root_message.created_at)

    def create(self, validated_data):
        messages_data = validated_data.pop("messages", [])
        version = Version.objects.create(**validated_data)
        for message_data in messages_data:
            Message.objects.create(version=version, **message_data)
        return version

    def update(self, instance, validated_data):
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

        instance.conversation = validated_data.get("conversation", instance.conversation)
        instance.parent_version = validated_data.get("parent_version", instance.parent_version)
        instance.root_message = validated_data.get("root_message", instance.root_message)
        instance.save()

        messages_data = validated_data.pop("messages", [])
        for message_data in messages_data:
            if "id" in message_data:
                try:
                    message = Message.objects.get(id=message_data["id"], version=instance)
                    message.content = message_data.get("content", message.content)
                    message.role = message_data.get("role", message.role)
                    message.save()
                except Message.DoesNotExist:
                    raise ValidationError(f"Message with ID {message_data['id']} not found for this version.")
            else:
                Message.objects.create(version=instance, **message_data)

        return instance


class ConversationSerializer(serializers.ModelSerializer):
    versions = VersionSerializer(many=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "active_version",
            "versions",
            "modified_at",
            "summary",
        ]

    def create(self, validated_data):
        versions_data = validated_data.pop("versions", [])
        conversation = Conversation.objects.create(**validated_data)
        for version_data in versions_data:
            version_serializer = VersionSerializer(data=version_data)
            version_serializer.is_valid(raise_exception=True)
            version_serializer.save(conversation=conversation)
        return conversation

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)

        active_version_id = validated_data.get("active_version")
        if active_version_id:
            try:
                active_version = Version.objects.get(id=active_version_id)
                instance.active_version = active_version
            except Version.DoesNotExist:
                raise ValidationError(f"Active version with ID {active_version_id} not found.")

        instance.save()

        versions_data = validated_data.pop("versions", [])
        for version_data in versions_data:
            if "id" in version_data:
                try:
                    version = Version.objects.get(id=version_data["id"], conversation=instance)
                    version_serializer = VersionSerializer(version, data=version_data)
                except Version.DoesNotExist:
                    raise ValidationError(f"Version with ID {version_data['id']} not found for this conversation.")
            else:
                version_serializer = VersionSerializer(data=version_data)

            version_serializer.is_valid(raise_exception=True)
            version_serializer.save(conversation=instance)

        return instance