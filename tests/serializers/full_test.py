from rest_framework import serializers
from ..models import (
    ProductiveTest,
    Test,
    ReceptiveTest,
    ReceptivePart,
    ReceptiveQuestion,
    ReceptiveAnswer,
)

from django.db import transaction
from ..utils.gcs_cleanup import cleanup_productive_test_on_update


class ReceptiveAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceptiveAnswer
        fields = [
            "id",
            "option_label",
            "answer_text",
            "is_correct",
            "resources",
        ]
        read_only_fields = ["id"]


class ReceptiveQuestionSerializer(serializers.ModelSerializer):
    receptive_answers = ReceptiveAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = ReceptiveQuestion
        fields = [
            "id",
            "question_number",
            "content",
            "explanation",
            "score",
            "resources",
            "receptive_answers",
        ]
        read_only_fields = ["id"]


class ReceptivePartSerializer(serializers.ModelSerializer):
    receptive_questions = ReceptiveQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = ReceptivePart
        fields = [
            "id",
            "order",
            "format",
            "description",
            "content",
            "score",
            "resources",
            "receptive_questions",
        ]


class ReceptiveTestSerializer(serializers.ModelSerializer):
    receptive_parts = ReceptivePartSerializer(many=True, read_only=True)

    class Meta:
        model = ReceptiveTest
        fields = [
            "total_score",
            "receptive_parts",
        ]


class ReceptiveTestRetrieveSerializer(serializers.ModelSerializer):
    receptive_test = ReceptiveTestSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        teacher = getattr(user, "teacher", None)
        return bool(teacher and obj.created_by_id == teacher.pk)

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
            "is_owner",
            "receptive_test",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# Public (student-facing) serializers: same shape as the full ones but with
# answer-key fields (`is_correct`, `explanation`) stripped so they cannot leak
# to a student inspecting the network response before submitting the test.
class ReceptiveAnswerPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceptiveAnswer
        fields = [
            "id",
            "option_label",
            "answer_text",
            "resources",
        ]
        read_only_fields = ["id"]


class ReceptiveQuestionPublicSerializer(serializers.ModelSerializer):
    receptive_answers = ReceptiveAnswerPublicSerializer(many=True, read_only=True)

    class Meta:
        model = ReceptiveQuestion
        fields = [
            "id",
            "question_number",
            "content",
            "score",
            "resources",
            "receptive_answers",
        ]
        read_only_fields = ["id"]


class ReceptivePartPublicSerializer(serializers.ModelSerializer):
    receptive_questions = ReceptiveQuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = ReceptivePart
        fields = [
            "id",
            "order",
            "format",
            "description",
            "content",
            "score",
            "resources",
            "receptive_questions",
        ]


class ReceptiveTestPublicSerializer(serializers.ModelSerializer):
    receptive_parts = ReceptivePartPublicSerializer(many=True, read_only=True)

    class Meta:
        model = ReceptiveTest
        fields = [
            "total_score",
            "receptive_parts",
        ]


class ReceptiveTestRetrievePublicSerializer(serializers.ModelSerializer):
    receptive_test = ReceptiveTestPublicSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        teacher = getattr(user, "teacher", None)
        return bool(teacher and obj.created_by_id == teacher.pk)

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
            "is_owner",
            "receptive_test",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductiveTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductiveTest
        fields = [
            "format",
            "topic",
            "description",
            "min_word",
            "glue_text",
            "glue_resources",
        ]
    
    def update(self, instance, validated_data):
        """
        Update ProductiveTest with GCS cleanup for changed resources
        """
        # Cleanup old GCS resources if description or glue_resources changed
        cleanup_productive_test_on_update(instance, validated_data)
        
        # Perform the update
        return super().update(instance, validated_data)


class ProductiveTestRetrieveSerializer(serializers.ModelSerializer):
    productive_test = ProductiveTestSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        teacher = getattr(user, "teacher", None)
        return bool(teacher and obj.created_by_id == teacher.pk)

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
            "is_owner",
            "productive_test",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductiveTestUpdateSerializer(serializers.ModelSerializer):
    productive_test = ProductiveTestSerializer(required=False)

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
            "productive_test",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "title": {"required": False},
            "type": {"required": False},
            "level": {"required": False},
            "skill": {"required": False},
            "time": {"required": False},
            "description": {"required": False},
            "status": {"required": False},
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        productive_test_data = validated_data.pop("productive_test", None)

        instance = super().update(instance, validated_data)

        if productive_test_data:
            productive_test = getattr(instance, "productive_test", None)
            if productive_test is None:
                return instance

            serializer = ProductiveTestSerializer(
                productive_test,
                data=productive_test_data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return instance


class ReceptiveAnswerUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["create", "update", "delete"])
    id = serializers.IntegerField(required=False)
    option_label = serializers.CharField(max_length=1, required=False)
    answer_text = serializers.CharField(required=False)
    is_correct = serializers.BooleanField(required=False)
    resources = serializers.JSONField(required=False)


class ReceptiveQuestionUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["create", "update", "delete"])
    id = serializers.IntegerField(required=False)
    question_number = serializers.IntegerField(required=False)
    content = serializers.CharField(required=False)
    explanation = serializers.CharField(required=False, allow_blank=True)
    score = serializers.IntegerField(required=False)
    resources = serializers.JSONField(required=False)
    receptive_answers = ReceptiveAnswerUpdateSerializer(many=True, required=False)


class ReceptivePartUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["create", "update", "delete"])
    id = serializers.IntegerField(required=False)
    order = serializers.IntegerField(required=False)
    format = serializers.CharField(max_length=1, required=False)
    description = serializers.CharField(required=False)
    content = serializers.CharField(required=False)
    # score is calculated from questions, not allowed to patch
    resources = serializers.JSONField(required=False)
    receptive_questions = ReceptiveQuestionUpdateSerializer(many=True, required=False)


class ReceptiveTestUpdateSerializer(serializers.Serializer):
    # total_score is calculated automatically, not allowed to patch
    receptive_parts = ReceptivePartUpdateSerializer(many=True, required=False)


class ReceptiveTestFullUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(required=False)
    type = serializers.CharField(max_length=1, required=False)
    level = serializers.CharField(max_length=2, required=False)
    skill = serializers.CharField(max_length=1, required=False)
    time = serializers.IntegerField(required=False)
    description = serializers.CharField(required=False)
    status = serializers.CharField(max_length=1, required=False)
    receptive_test = ReceptiveTestUpdateSerializer(required=False)
