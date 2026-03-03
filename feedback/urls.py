from .views import AIFeedbackForSpeakingAPIView, AIFeedbackForWritingAPIView

from django.urls import path

urlpatterns = [
    path(
        "ai-feedback/writing",
        AIFeedbackForWritingAPIView.as_view(),
        name="ai-feedback-writing",
    ),
    path(
        "ai-feedback/speaking",
        AIFeedbackForSpeakingAPIView.as_view(),
        name="ai-feedback-speaking",
    ),
]
