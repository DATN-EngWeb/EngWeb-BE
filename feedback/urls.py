from .views import (
    AIFeedbackForReadingAPIView,
    AIFeedbackForSpeakingAPIView,
    AIFeedbackForWritingAPIView,
    TeacherListCreateTestFeedbackAPIView,
    TeacherRetrieveUpdateDestroyTestFeedbackAPIView,
)

from django.urls import path

urlpatterns = [
    path(
        "ai-feedback/writing",
        AIFeedbackForWritingAPIView.as_view(),
        name="ai-feedback-writing",
    ),
    path(
        "ai-feedback/reading",
        AIFeedbackForReadingAPIView.as_view(),
        name="ai-feedback-reading",
    ),
    path(
        "ai-feedback/speaking",
        AIFeedbackForSpeakingAPIView.as_view(),
        name="ai-feedback-speaking",
    ),
    path(
        "test-feedbacks",
        TeacherListCreateTestFeedbackAPIView.as_view(),
        name="test-feedback-list-create",
    ),
    path(
        "test-feedbacks/<int:feedback_id>",
        TeacherRetrieveUpdateDestroyTestFeedbackAPIView.as_view(),
        name="test-feedback-retrieve-update-delete",
    ),
]
