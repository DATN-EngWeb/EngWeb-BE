from rest_framework import serializers

from .models import UserLevel


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
