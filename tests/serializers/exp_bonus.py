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


class EXPBonusCalculateRequestSerializer(serializers.Serializer):
    """
    Serializer for EXP Bonus calculation request
    """

    test_id = serializers.IntegerField(
        help_text="ID of the test",
        min_value=1,
    )
    completion_percentage = serializers.FloatField(
        help_text="Completion percentage of the test (0-100)",
        min_value=0.0,
        max_value=100.0,
    )


class EXPBonusCalculateResponseSerializer(serializers.Serializer):
    """
    Serializer for EXP Bonus calculation response
    """

    test_id = serializers.IntegerField()
    test_title = serializers.CharField()
    skill = serializers.CharField()
    level = serializers.CharField()
    completion_percentage = serializers.FloatField()
    completed_bonus = serializers.IntegerField(
        help_text="Base bonus points for completing the test"
    )
    exp_percentage = serializers.FloatField(
        help_text="EXP percentage based on completion percentage"
    )
    exp_earned = serializers.FloatField(
        help_text="Total EXP earned = completed_bonus * exp_percentage / 100"
    )
    rating = serializers.CharField()
    feedback_message = serializers.CharField()
