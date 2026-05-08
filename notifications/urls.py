from django.urls import path

from .views import (
    NotificationListAPIView,
    NotificationMarkReadAPIView,
    NotificationMarkAllReadAPIView,
    NotificationUnreadCountAPIView,
)

urlpatterns = [
    path("read-all", NotificationListAPIView.as_view(), name="notification-list"),
    path("mark-all-read", NotificationMarkAllReadAPIView.as_view(), name="notification-mark-all-read"),
    path("unread-count", NotificationUnreadCountAPIView.as_view(), name="notification-unread-count"),
    path("mark-read/<int:id>", NotificationMarkReadAPIView.as_view(), name="notification-mark-read"),
]
