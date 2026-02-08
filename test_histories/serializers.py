from rest_framework import serializers
from django.utils import timezone
from .models import ProductiveTestHistory
from accounts.models import Student
from tests.models import ProductiveTest


class ProductiveTestHistorySerializer(serializers.ModelSerializer):
    """Serializer for list and create ProductiveTestHistory"""

    class Meta:
        model = ProductiveTestHistory
        fields = [
            "id",
            "student",
            "productive_test",
            "attempt",
            "type",
            "start_time",
            "end_time",
            "total_time",
            "audio_path",
            "user_answer_text",
            "user_note_text",
            "ai_feedback",
            "earned_bonus_point",
        ]
        read_only_fields = [
            "id",
            "student",
            "attempt",
            "total_time",
            "earned_bonus_point",
        ]

    def validate(self, attrs):
        """Validate the data"""
        # For create operations
        if not self.instance:
            productive_test = attrs.get("productive_test")

            # Check if productive_test exists
            if not ProductiveTest.objects.filter(pk=productive_test.pk).exists():
                raise serializers.ValidationError(
                    {"productive_test": "Productive test does not exist."}
                )

        # Validate times
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if start_time and start_time > timezone.now():
            raise serializers.ValidationError(
                {"start_time": "Start time cannot be in the future."}
            )

        if end_time and start_time and end_time < start_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )

        # For submission, end_time should be provided
        type_value = attrs.get("type", self.instance.type if self.instance else "D")
        if type_value == "S" and not (
            end_time or (self.instance and self.instance.end_time)
        ):
            raise serializers.ValidationError(
                {"end_time": "End time is required for submissions."}
            )

        return attrs
