from rest_framework import serializers
from ..models import (
    ProductiveTest,
    Test,
    ReceptiveTest,
    ReceptivePart,
    ReceptiveQuestion,
    ReceptiveAnswer,
)


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
