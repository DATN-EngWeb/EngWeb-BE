from django.urls import path

from .views import UserLevelListAPIView, UserLevelRetrieveAPIView

app_name = "user_progress"

urlpatterns = [
    path("levels", UserLevelListAPIView.as_view(), name="user-level-list"),
    path(
        "levels/<int:level_number>",
        UserLevelRetrieveAPIView.as_view(),
        name="user-level-retrieve",
    ),
]
