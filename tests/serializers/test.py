from ..models import Test, ReceptiveTest, ProductiveTest

from rest_framework import serializers


class ReceptiveTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceptiveTest
        fields = ["total_score"]


class ProductiveTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductiveTest
        fields = ["format", "topic", "min_word"]


class TestSerializer(serializers.ModelSerializer):
    test_details = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    progress_status = serializers.SerializerMethodField()
    submitted = serializers.SerializerMethodField()

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
            "status",
            "created_at",
            "updated_at",
            "test_details",
            "created_by",
            "progress_status",
            "submitted",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def get_test_details(self, obj):
        if obj.type == "R":
            try:
                receptive_test = obj.receptive_test
                return ReceptiveTestSerializer(receptive_test).data
            except ReceptiveTest.DoesNotExist:
                return None
        elif obj.type == "P":
            try:
                productive_test = obj.productive_test
                return ProductiveTestSerializer(productive_test).data
            except ProductiveTest.DoesNotExist:
                return None
        return None

    def get_created_by(self, obj):
        if obj.created_by:
            user = obj.created_by.user
            return {
                "id": obj.created_by.pk,
                "full_name": user.full_name,
                "avatar": user.avatar.url if user.avatar else None,
            }
        return None

    def get_progress_status(self, obj):
        """
        Calculate progress status for student.
        Returns: "completed", "draft", "none", or None if not requested/not a student
        """
        # Check if progress_status was requested in context
        request_progress = self.context.get("request_progress_status", False)
        if not request_progress:
            return None

        # Get student from context
        student = self.context.get("student")
        if not student:
            return None

        # Import here to avoid circular import
        from test_histories.models import ProductiveTestHistory

        # Check history based on test type
        if obj.type == "P":  # Productive test
            try:
                productive_test = obj.productive_test

                # Check if student has any draft
                has_draft = ProductiveTestHistory.objects.filter(
                    student=student, productive_test=productive_test, type="D"
                ).exists()

                if has_draft:
                    return "draft"
                # Check if student has any submission
                has_submission = ProductiveTestHistory.objects.filter(
                    student=student, productive_test=productive_test, type="S"
                ).exists()

                if has_submission:
                    return "completed"

                return "none"
            except:
                return "none"
        else:  # Receptive test - no history tracking yet
            # For receptive tests, you may implement similar logic when ReceptiveTestHistory is available
            return "none"

    def get_submitted(self, obj):
        """
        Calculate total number of submissions for this test.
        Returns the count of all submission records (type='S') for Productive or Receptive tests.
        Returns None if not requested via 'submitted' parameter.
        
        OPTIMIZATION: If 'submitted' was already annotated in queryset (for ordering),
        reuse that value instead of querying again.
        """
        # Check if submitted was requested in context
        request_submitted = self.context.get("request_submitted", False)
        if not request_submitted:
            return None

        # OPTIMIZATION: Check if 'submitted' was already annotated (from get_queryset for ordering)
        # If yes, reuse that value to avoid duplicate query
        if hasattr(obj, "submitted"):
            return obj.submitted

        # If not annotated, query manually (fallback for edge cases)
        # Import here to avoid circular import
        from test_histories.models import ProductiveTestHistory, ReceptiveTestHistory

        if obj.type == "P":
            try:
                productive_test = obj.productive_test
                return ProductiveTestHistory.objects.filter(
                    productive_test=productive_test, type="S"
                ).count()
            except:
                return 0
        elif obj.type == "R":
            try:
                receptive_test = obj.receptive_test
                return ReceptiveTestHistory.objects.filter(
                    receptive_test=receptive_test, type="S"
                ).count()
            except:
                return 0

        return 0

    def to_representation(self, instance):
        """
        Override to remove progress_status and submitted fields if they're None
        """
        representation = super().to_representation(instance)

        # Remove progress_status field if it's None (not requested)
        if representation.get("progress_status") is None:
            representation.pop("progress_status", None)

        # Remove submitted field if it's None (not requested)
        if representation.get("submitted") is None:
            representation.pop("submitted", None)

        return representation

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
