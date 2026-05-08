from django.urls import path

from .views import (
    AssistantConversationArchiveAPIView,
    AssistantConversationListCreateAPIView,
    AssistantConversationMessageAPIView,
    AssistantConversationRenameAPIView,
    AssistantConversationRetrieveAPIView,
    AssistantQuotaAPIView,
)

urlpatterns = [
    path("conversations", AssistantConversationListCreateAPIView.as_view(), name="assistant-conversation-list-create"),
    path("conversations/<int:pk>", AssistantConversationRetrieveAPIView.as_view(), name="assistant-conversation-retrieve"),
    path("conversations/<int:conversation_id>/archive", AssistantConversationArchiveAPIView.as_view(), name="assistant-conversation-archive"),
    path("conversations/<int:conversation_id>/rename", AssistantConversationRenameAPIView.as_view(), name="assistant-conversation-rename"),
    path("conversations/<int:conversation_id>/messages", AssistantConversationMessageAPIView.as_view(), name="assistant-conversation-message"),
    path("quota", AssistantQuotaAPIView.as_view(), name="assistant-quota"),
]
