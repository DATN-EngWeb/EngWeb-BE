from ..models import Test

from rest_framework import serializers


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = [
            "id",
            "title",
            "type",
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
        }

    def validate(self, attrs):
        errors = {}

        # Validate title
        title = attrs.get("title", "").strip()
        if not title:
            errors["title"] = "This field is required."

        # Validate type
        test_type = attrs.get("type")
        if not test_type:
            errors["type"] = "This field is required."
        elif test_type not in ["R", "P"]:
            errors["type"] = "Must be one of: R (Receptive), P (Productive)."

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

        # Validate type-skill compatibility
        if test_type and skill:
            if test_type == "R" and skill not in ["R", "L"]:
                errors["skill"] = (
                    "Receptive test (type=R) only supports Reading (R) or Listening (L) skills."
                )
            elif test_type == "P" and skill not in ["S", "W"]:
                errors["skill"] = (
                    "Productive test (type=P) only supports Speaking (S) or Writing (W) skills."
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

        # Validate status (allow only D, I, P on create)
        status = attrs.get("status")
        if status and status not in ["D", "I", "P"]:
            errors["status"] = (
                "Must be one of: D (Draft), I (In Review), P (Published)."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        # Set default status to Draft if not provided
        validated_data.setdefault("status", "D")

        # Get creator (teacher) from context
        request = self.context.get("request")
        if request:
            teacher = getattr(request.user, "teacher", None)
            if teacher:
                validated_data["created_by"] = teacher

        test = Test.objects.create(**validated_data)
        return test
