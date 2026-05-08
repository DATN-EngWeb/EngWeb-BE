from rest_framework import serializers

from .models import UserLevel, StreakRewardRule


class UserLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLevel
        fields = [
            "id",
            "level_number",
            "level_title",
            "level_icon",
            "min_xp",
            "max_xp",
        ]


class StreakRewardRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreakRewardRule
        fields = ["id", "streak_day", "xp_reward", "ai_turn_reward"]
