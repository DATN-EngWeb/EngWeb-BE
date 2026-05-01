from rest_framework import serializers

from .models import AssistantConversation, AssistantMessage
from .utils import normalize_mode


class AssistantMessageSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    mode = serializers.SerializerMethodField()

    class Meta:
        model = AssistantMessage
        fields = [
            "id",
            "role",
            "mode",
            "content",
            "token_usage_prompt",
            "token_usage_completion",
            "token_usage_total",
            "status",
            "created_at",
        ]
    
    def get_content(self, obj):
        """Return parsed JSON when `content` contains JSON, else raw text.

        - If `content` is a JSON string, return parsed object.
        - Otherwise return the plain text string.
        """
        try:
            raw = getattr(obj, "content", None)
            if raw is None:
                return None

            raw = raw.strip()
            if not raw:
                return ""

            import json

            try:
                return json.loads(raw)
            except Exception:
                return raw
        except Exception:
            return None

    def get_mode(self, obj):
        mode = getattr(obj, "mode", None) or getattr(getattr(obj, "conversation", None), "mode", None)
        return normalize_mode(mode)


class AssistantConversationMessagesMetaSerializer(serializers.Serializer):
    limit = serializers.IntegerField()
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    has_more = serializers.BooleanField()
    oldest_id = serializers.IntegerField(allow_null=True)
    newest_id = serializers.IntegerField(allow_null=True)
    before_id = serializers.IntegerField(allow_null=True)


class AssistantConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantConversation
        fields = [
            "id",
            "title",
            "is_title_auto",
            "mode",
            "level",
            "system_prompt_version",
            "last_message_at",
            "is_archived",
            "created_at",
            "updated_at",
        ]


class AssistantConversationDetailSerializer(AssistantConversationSerializer):
    messages = serializers.SerializerMethodField()
    messages_meta = serializers.SerializerMethodField()

    class Meta(AssistantConversationSerializer.Meta):
        fields = AssistantConversationSerializer.Meta.fields + ["messages", "messages_meta"]

    def get_messages(self, obj):
        messages = self.context.get("messages")
        if messages is None:
            messages = obj.messages.all()
        return AssistantMessageSerializer(messages, many=True, context=self.context).data

    def get_messages_meta(self, obj):
        return self.context.get("messages_meta", {})


class AssistantConversationCreateSerializer(serializers.ModelSerializer):
    mode = serializers.CharField(required=False)
    title = serializers.CharField(required=False, allow_blank=True)
    level = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = AssistantConversation
        fields = ["title", "mode", "level"]

    def validate_mode(self, value):
        return normalize_mode(value)

    def create(self, validated_data):
        user = self.context["request"].user
        title = (validated_data.pop("title", "") or "").strip()
        mode = normalize_mode(validated_data.pop("mode", None))
        level = validated_data.pop("level", None)

        if title:
            is_title_auto = False
        else:
            title = "New Chat"
            is_title_auto = True

        return AssistantConversation.objects.create(
            user=user,
            title=title,
            is_title_auto=is_title_auto,
            mode=mode,
            level=level,
        )


class AssistantConversationRenameSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False, max_length=120)


class AssistantSendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=False)
    mode = serializers.CharField(required=False)
    context = serializers.JSONField(required=False)

    def validate_mode(self, value):
        return normalize_mode(value)

    def validate_context(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("context must be a JSON object")
        return value
        
