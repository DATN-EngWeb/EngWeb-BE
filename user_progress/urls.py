from django.urls import path

from .views import (
    UserLevelListAPIView,
    UserLevelRetrieveAPIView,
    CurrentUserStreakAPIView,
    CurrentUserAITurnView,
    StreakRewardRuleListAPIView,
    StreakRewardRuleRetrieveAPIView,
)

app_name = "user_progress"

urlpatterns = [
    path("levels", UserLevelListAPIView.as_view(), name="user-level-list"),
    path("streak", CurrentUserStreakAPIView.as_view(), name="current-user-streak"),
    path("ai-turn", CurrentUserAITurnView.as_view(), name="current-user-ai-turn"),
    path(
        "levels/<int:level_number>",
        UserLevelRetrieveAPIView.as_view(),
        name="user-level-retrieve",
    ),
    path(
        "streak-reward-rules",
        StreakRewardRuleListAPIView.as_view(),
        name="streak-reward-rule-list",
    ),
    path(
        "streak-reward-rules/<int:streak_day>",
        StreakRewardRuleRetrieveAPIView.as_view(),
        name="streak-reward-rule-retrieve",
    ),
]
