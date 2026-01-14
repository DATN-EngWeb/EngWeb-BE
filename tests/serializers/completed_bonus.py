from rest_framework import serializers

from ..models import CompletedBonus


class CompletedBonusSerializer(serializers.ModelSerializer):
    """
    Serializer for CompletedBonus model
    """

    class Meta:
        model = CompletedBonus
        fields = ["id", "skill", "level", "completed_bonus"]
        read_only_fields = ["id"]
