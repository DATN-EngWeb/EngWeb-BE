from rest_framework import serializers

from ..models import WritingCriteriaTemplate


class WritingCriteriaTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for WritingCriteriaTemplate model
    """

    class Meta:
        model = WritingCriteriaTemplate
        fields = [
            "id",
            "level",
            "band",
            "content",
            "communicative_achievement",
            "organisation",
            "language",
        ]
        read_only_fields = ["id"]
