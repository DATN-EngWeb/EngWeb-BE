from .views import AIFeedbackForWritingAPIView

from django.urls import path

urlpatterns = [
    path("ai-feedback/writing", AIFeedbackForWritingAPIView.as_view(), name="ai-feedback-writing"),
]
