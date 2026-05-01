from django.conf import settings
from django.db import models
from django.utils import timezone


class AssistantConversation(models.Model):
    MODE_TRANSLATE = "translate"
    MODE_GRAMMAR = "grammar"
    MODE_VOCABULARY = "vocabulary"
    MODE_BRAINSTORM = "brainstorm"
    MODE_GENERAL = "general"

    MODE_CHOICES = [
        (MODE_TRANSLATE, "Translate"),
        (MODE_GRAMMAR, "Grammar"),
        (MODE_VOCABULARY, "Vocabulary"),
        (MODE_BRAINSTORM, "Brainstorm"),
        (MODE_GENERAL, "General"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_conversations",
    )
    title = models.CharField(max_length=120, default="New Chat")
    is_title_auto = models.BooleanField(default=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_GENERAL)
    level = models.CharField(max_length=32, null=True, blank=True)
    system_prompt_version = models.CharField(max_length=32, default="v1")
    last_message_at = models.DateTimeField(default=timezone.now)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assistant_conversation"
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "last_message_at"]),
            models.Index(fields=["user", "is_archived"]),
        ]


class AssistantMessage(models.Model):
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_TOOL = "tool"

    ROLE_CHOICES = [
        (ROLE_SYSTEM, "System"),
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
        (ROLE_TOOL, "Tool"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    conversation = models.ForeignKey(
        AssistantConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    mode = models.CharField(max_length=20, choices=AssistantConversation.MODE_CHOICES, null=True, blank=True)
    content = models.TextField()
    token_usage_prompt = models.PositiveIntegerField(null=True, blank=True)
    token_usage_completion = models.PositiveIntegerField(null=True, blank=True)
    token_usage_total = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assistant_message"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["status"]),
        ]


class AssistantQuota(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_quota",
    )
    limit = models.PositiveIntegerField(default=50)
    used = models.PositiveIntegerField(default=0)
    period_seconds = models.PositiveIntegerField(default=43200)
    period_start = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assistant_quota"
