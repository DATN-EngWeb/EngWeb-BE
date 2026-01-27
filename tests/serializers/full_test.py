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
            "base_qualified_bonus",
            "receptive_parts",
        ]


class ReceptiveTestRetrieveSerializer(serializers.ModelSerializer):
    receptive_test = ReceptiveTestSerializer(read_only=True)

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


class ProductiveTestRetrieveSerializer(serializers.ModelSerializer):
    productive_test = ProductiveTestSerializer(read_only=True)

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
    action = serializers.ChoiceField(choices=["update", "delete"])
    id = serializers.IntegerField()
    option_label = serializers.CharField(max_length=1, required=False)
    answer_text = serializers.CharField(required=False)
    is_correct = serializers.BooleanField(required=False)
    resources = serializers.JSONField(required=False)


class ReceptiveQuestionUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["update", "delete"])
    id = serializers.IntegerField()
    question_number = serializers.IntegerField(required=False)
    content = serializers.CharField(required=False)
    explanation = serializers.CharField(required=False)
    score = serializers.IntegerField(required=False)
    resources = serializers.JSONField(required=False)
    receptive_answers = ReceptiveAnswerUpdateSerializer(many=True, required=False)


class ReceptivePartUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["update", "delete"])
    id = serializers.IntegerField()
    order = serializers.IntegerField(required=False)
    format = serializers.CharField(max_length=1, required=False)
    description = serializers.CharField(required=False)
    content = serializers.CharField(required=False)
    # score is calculated from questions, not allowed to patch
    resources = serializers.JSONField(required=False)
    receptive_questions = ReceptiveQuestionUpdateSerializer(many=True, required=False)


class ReceptiveTestUpdateSerializer(serializers.Serializer):
    # total_score is calculated automatically, not allowed to patch
    base_qualified_bonus = serializers.IntegerField(required=False)
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
