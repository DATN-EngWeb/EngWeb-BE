"""
URL configuration for storage app
"""

from django.urls import path
from .views import RequestPresignedURLView, ConfirmUploadView

urlpatterns = [
    path(
        "presigned-urls",
        RequestPresignedURLView.as_view(),
        name="presigned-urls",
    ),
    path("confirmation", ConfirmUploadView.as_view(), name="confirmation"),
]
