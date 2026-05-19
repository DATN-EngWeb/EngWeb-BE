from rest_framework import serializers

from ..models import SpeakingCriteriaTemplate


class SpeakingCriteriaTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for SpeakingCriteriaTemplate model
    """

    class Meta:
        model = SpeakingCriteriaTemplate
        fields = [
            "id",
            "level",
            "band",
            "grammar_and_vocabulary",
            "discourse_management",
            "pronunciation",
            "task_achievement",
        ]
        read_only_fields = ["id"]