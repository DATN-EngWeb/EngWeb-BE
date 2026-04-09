from django.urls import path

from .views import (
    UserLevelListAPIView,
    UserLevelRetrieveAPIView,
    CurrentUserStreakAPIView,
)

app_name = "user_progress"

urlpatterns = [
    path("levels", UserLevelListAPIView.as_view(), name="user-level-list"),
    path("streak", CurrentUserStreakAPIView.as_view(), name="current-user-streak"),
    path(
        "levels/<int:level_number>",
        UserLevelRetrieveAPIView.as_view(),
        name="user-level-retrieve",
    ),
]
