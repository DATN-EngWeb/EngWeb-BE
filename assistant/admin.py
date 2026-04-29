from django.contrib import admin

from .models import AssistantConversation, AssistantMessage, AssistantQuota


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "mode", "is_archived", "last_message_at")
    search_fields = ("title", "user__username", "user__email")
    list_filter = ("mode", "is_archived")


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "status", "created_at")
    list_filter = ("role", "status")
    search_fields = ("conversation__title", "content")


@admin.register(AssistantQuota)
class AssistantQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "limit", "used", "period_seconds", "period_start", "updated_at")
    search_fields = ("user__username", "user__email")
