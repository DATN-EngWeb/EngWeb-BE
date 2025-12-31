from .models import Test, ProductiveTest, ReceptiveTest

from rest_framework import serializers


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = [
            "id",
            "title",
            "level",
            "skill",
            "time",
            "description",
            "completed_bonus",
            "status",
            "created_at",
            "updated_at",
            "created_by",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
            "created_by": {"read_only": True},
            "status": {"read_only": True},  # Status will be set by view logic
        }

    def validate(self, attrs):
        errors = {}

        # Validate title
        title = attrs.get("title", "").strip()
        if not title:
            errors["title"] = "This field is required."

        # Validate level
        level = attrs.get("level")
        if level and level not in ["B1", "B2", "A1", "A2"]:
            errors["level"] = "Must be one of: B1, B2, A1, A2."

        # Validate skill
        skill = attrs.get("skill")
        if skill and skill not in ["R", "L", "S", "W"]:
            errors["skill"] = (
                "Must be one of: R (Reading), L (Listening), S (Speaking), W (Writing)."
            )

        # Validate time
        time_value = attrs.get("time")
        if time_value is None:
            errors["time"] = "This field is required."
        elif isinstance(time_value, str):
            try:
                attrs["time"] = int(time_value)
            except ValueError:
                errors["time"] = "Must be a valid integer."
        elif isinstance(time_value, int):
            if time_value < 1:
                errors["time"] = "Must be at least 1 minute."

        # Validate description
        description = attrs.get("description", "").strip()
        if not description:
            errors["description"] = "This field is required."

        # Validate completed_bonus
        completed_bonus = attrs.get("completed_bonus", 0)
        if isinstance(completed_bonus, str):
            try:
                attrs["completed_bonus"] = int(completed_bonus)
            except ValueError:
                errors["completed_bonus"] = "Must be a valid integer."
        elif isinstance(completed_bonus, int):
            if completed_bonus < 0:
                errors["completed_bonus"] = "Must be a non-negative integer."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        # Set default status to Draft
        validated_data["status"] = "D"

        # Get creator (teacher) from context
        request = self.context.get("request")
        if request:
            teacher = getattr(request.user, "teacher", None)
            if teacher:
                validated_data["created_by"] = teacher

        test = Test.objects.create(**validated_data)
        return test
