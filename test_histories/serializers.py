from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import ProductiveTestHistory, ReceptiveTestHistory, ReceptiveAnswerHistory
from accounts.models import Student
from tests.models import (
    ProductiveTest,
    ReceptiveTest,
    ReceptiveQuestion,
    ReceptiveAnswer,
)
import json

class ProductiveTestHistorySerializer(serializers.ModelSerializer):
    """Serializer for list and create ProductiveTestHistory"""

    ai_feedback = serializers.SerializerMethodField()
    is_shared = serializers.SerializerMethodField()
    post_id = serializers.SerializerMethodField()

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
            "is_shared",
            "post_id",
        ]
        read_only_fields = [
            "id",
            "student",
            "attempt",
            "earned_bonus_point",
        ]

    def get_is_shared(self, obj):
        """Check if this test history has been shared to forum"""
        # Only query if requested via context
        if not self.context.get('include_is_shared', False):
            return None
        
        return obj.posts.exists()
    
    def get_post_id(self, obj):
        """Get the post ID if this test history has been shared to forum"""
        # Only query if requested via context
        if not self.context.get('include_is_shared', False):
            return None
        
        post = obj.posts.first()
        return post.id if post else None
    
    def to_representation(self, instance):
        """Remove is_shared and post_id fields from response if not requested"""
        data = super().to_representation(instance)
        if not self.context.get('include_is_shared', False):
            data.pop('is_shared', None)
            data.pop('post_id', None)
        return data
        
    def get_ai_feedback(self, obj):
        if not obj.ai_feedback:
            return None
        if isinstance(obj.ai_feedback, dict):
            return obj.ai_feedback
        try:
            return json.loads(obj.ai_feedback)
        except (TypeError, json.JSONDecodeError):
            return obj.ai_feedback

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


class ReceptiveAnswerHistorySerializer(serializers.Serializer):
    """Serializer for answer history within submission"""

    receptive_question = serializers.PrimaryKeyRelatedField(
        queryset=ReceptiveQuestion.objects.all()
    )
    receptive_answer = serializers.PrimaryKeyRelatedField(
        queryset=ReceptiveAnswer.objects.all(), required=False, allow_null=True
    )
    user_answer_text = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def validate(self, attrs):
        """Validate answer history data"""
        receptive_question = attrs.get("receptive_question")
        receptive_answer = attrs.get("receptive_answer")
        user_answer_text = attrs.get("user_answer_text")

        # At least one of receptive_answer or user_answer_text must be provided
        if not receptive_answer and not user_answer_text:
            raise serializers.ValidationError(
                "Either receptive_answer or user_answer_text must be provided."
            )

        # Get question format to validate correct data type
        part_format = receptive_question.receptive_part.format

        # Multiple Choice formats (A,B,C,F,G,H) - must have receptive_answer
        if part_format in ["A", "B", "C", "F", "G", "H"]:
            if not receptive_answer:
                raise serializers.ValidationError(
                    {
                        "receptive_answer": f"Question {receptive_question.id} has format '{part_format}' (Multiple Choice) and requires receptive_answer."
                    }
                )
            if user_answer_text:
                raise serializers.ValidationError(
                    {
                        "user_answer_text": f"Question {receptive_question.id} has format '{part_format}' (Multiple Choice) and should not have user_answer_text."
                    }
                )
            # For Multiple Choice, answer must belong to this specific question
            if receptive_answer.receptive_question_id != receptive_question.id:
                raise serializers.ValidationError(
                    {
                        "receptive_answer": f"Answer {receptive_answer.id} does not belong to question {receptive_question.id}."
                    }
                )

        # Matching formats (E,J) - must have receptive_answer
        elif part_format in ["E", "J"]:
            if not receptive_answer:
                raise serializers.ValidationError(
                    {
                        "receptive_answer": f"Question {receptive_question.id} has format '{part_format}' (Matching) and requires receptive_answer."
                    }
                )
            if user_answer_text:
                raise serializers.ValidationError(
                    {
                        "user_answer_text": f"Question {receptive_question.id} has format '{part_format}' (Matching) and should not have user_answer_text."
                    }
                )
            # For Matching, answer must belong to the same part (not necessarily the same question)
            if (
                receptive_answer.receptive_question.receptive_part_id
                != receptive_question.receptive_part_id
            ):
                raise serializers.ValidationError(
                    {
                        "receptive_answer": f"Answer {receptive_answer.id} does not belong to the same part as question {receptive_question.id}."
                    }
                )

        # Fill in the blanks formats (D,I) - must have user_answer_text
        elif part_format in ["D", "I"]:
            if not user_answer_text:
                raise serializers.ValidationError(
                    {
                        "user_answer_text": f"Question {receptive_question.id} has format '{part_format}' (Fill in the Blanks) and requires user_answer_text."
                    }
                )
            if receptive_answer:
                raise serializers.ValidationError(
                    {
                        "receptive_answer": f"Question {receptive_question.id} has format '{part_format}' (Fill in the Blanks) and should not have receptive_answer."
                    }
                )

        return attrs


class ReceptiveTestHistorySerializer(serializers.ModelSerializer):
    """Serializer for creating and updating ReceptiveTestHistory with answer histories"""

    answer_histories = ReceptiveAnswerHistorySerializer(many=True, write_only=True)

    class Meta:
        model = ReceptiveTestHistory
        fields = [
            "id",
            "student",
            "receptive_test",
            "attempt",
            "type",
            "start_time",
            "end_time",
            "total_time",
            "total_score",
            "earned_bonus_point",
            "answer_histories",
        ]
        read_only_fields = [
            "id",
            "student",
            "attempt",
            "total_score",
            "earned_bonus_point",
        ]

    def validate(self, attrs):
        """Validate the data"""
        # For create operations, check if receptive_test exists
        if not self.instance:
            receptive_test = attrs.get("receptive_test")
            if not ReceptiveTest.objects.filter(pk=receptive_test.pk).exists():
                raise serializers.ValidationError(
                    {"receptive_test": "Receptive test does not exist."}
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

        # Validate that all questions belong to the receptive_test
        answer_histories_data = attrs.get("answer_histories", [])
        if answer_histories_data:
            # Get test instance: from attrs (create) or from instance (update)
            receptive_test = (
                attrs.get("receptive_test")
                if not self.instance
                else self.instance.receptive_test
            )

            for answer_data in answer_histories_data:
                question = answer_data.get("receptive_question")
                if question:
                    # Check if question belongs to the test through: question -> part -> test
                    if question.receptive_part.receptive_test_id != receptive_test.pk:
                        raise serializers.ValidationError(
                            {
                                "answer_histories": f"Question {question.pk} does not belong to receptive test {receptive_test.pk}."
                            }
                        )

        return attrs

    def _calculate_answer_score(self, question, selected_answer=None, user_text=None):
        """
        Calculate score for a single answer
        Returns: (is_correct, score)
        """
        # Get the format of the part this question belongs to
        part_format = question.receptive_part.format

        # Multiple Choice formats: A, B, C, F, G, H
        # Matching formats: E, J
        if part_format in ["A", "B", "C", "E", "F", "G", "H", "J"]:
            if not selected_answer:
                return False, 0

            # Check if selected_answer belongs to this question and is correct
            if (
                selected_answer.receptive_question_id == question.id
                and selected_answer.is_correct
            ):
                return True, question.score

            return False, 0

        # Fill in the blanks - Text: D, I
        elif part_format in ["D", "I"]:
            if not user_text:
                return False, 0

            # Get correct answer(s)
            correct_answers = question.receptive_answers.filter(is_correct=True)

            # Normalize user text for comparison
            user_text_normalized = user_text.strip().lower()

            # Check if user text matches any correct answer
            for correct_answer in correct_answers:
                if correct_answer.answer_text:
                    correct_text_normalized = correct_answer.answer_text.strip().lower()
                    if user_text_normalized == correct_text_normalized:
                        return True, question.score

            return False, 0

        return False, 0

    @transaction.atomic
    def create(self, validated_data):
        """Create ReceptiveTestHistory with answer histories"""
        answer_histories_data = validated_data.pop("answer_histories", [])

        # Get student from context (should be set in view)
        student = self.context.get("student")
        if not student:
            raise serializers.ValidationError(
                {"student": "Student is required in context."}
            )

        receptive_test = validated_data.get("receptive_test")
        type_value = validated_data.get("type")

        # Calculate attempt number based on submission count (same logic for Draft and Submission)
        submission_count = ReceptiveTestHistory.objects.filter(
            student=student, receptive_test=receptive_test, type="S"
        ).count()

        attempt = submission_count + 1

        # Create ReceptiveTestHistory
        receptive_test_history = ReceptiveTestHistory.objects.create(
            student=student, attempt=attempt, **validated_data
        )

        # Calculate total score and prepare answer histories for batch create
        total_score = 0
        answer_history_objects = []

        for answer_data in answer_histories_data:
            question = answer_data["receptive_question"]
            selected_answer = answer_data.get("receptive_answer")
            user_text = answer_data.get("user_answer_text")

            # Calculate score for this answer
            is_correct, score = self._calculate_answer_score(
                question, selected_answer, user_text
            )

            # Prepare ReceptiveAnswerHistory object
            answer_history_objects.append(
                ReceptiveAnswerHistory(
                    receptive_test_history=receptive_test_history,
                    receptive_question=question,
                    receptive_answer=selected_answer,
                    user_answer_text=user_text,
                    is_correct=is_correct,
                )
            )

            total_score += score

        # Batch create all answer histories
        if answer_history_objects:
            ReceptiveAnswerHistory.objects.bulk_create(answer_history_objects)

        # Update total_score
        receptive_test_history.total_score = total_score
        receptive_test_history.save(update_fields=["total_score"])

        # TODO: Calculate and update earned_bonus_point based on EXPBonusRule

        return receptive_test_history

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update ReceptiveTestHistory (for draft update or draft to submission conversion)"""
        answer_histories_data = validated_data.pop("answer_histories", [])

        # Update ReceptiveTestHistory fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # If answer_histories provided, recalculate scores
        if answer_histories_data:
            # Delete old answer histories before creating new ones
            instance.answer_histories.all().delete()

            # Calculate total score and prepare answer histories for batch create
            total_score = 0
            answer_history_objects = []

            for answer_data in answer_histories_data:
                question = answer_data["receptive_question"]
                selected_answer = answer_data.get("receptive_answer")
                user_text = answer_data.get("user_answer_text")

                # Calculate score for this answer
                is_correct, score = self._calculate_answer_score(
                    question, selected_answer, user_text
                )

                # Prepare ReceptiveAnswerHistory object
                answer_history_objects.append(
                    ReceptiveAnswerHistory(
                        receptive_test_history=instance,
                        receptive_question=question,
                        receptive_answer=selected_answer,
                        user_answer_text=user_text,
                        is_correct=is_correct,
                    )
                )

                total_score += score

            # Batch create all answer histories
            if answer_history_objects:
                ReceptiveAnswerHistory.objects.bulk_create(answer_history_objects)

            # Update total_score
            instance.total_score = total_score
            instance.save(update_fields=["total_score"])

        # TODO: Calculate and update earned_bonus_point based on EXPBonusRule

        return instance


class ReceptiveTestHistoryDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving ReceptiveTestHistory with answer details"""

    answer_histories = serializers.SerializerMethodField()
    student_username = serializers.CharField(
        source="student.user.username", read_only=True
    )
    test_title = serializers.CharField(
        source="receptive_test.test.title", read_only=True
    )

    class Meta:
        model = ReceptiveTestHistory
        fields = [
            "id",
            "student",
            "student_username",
            "receptive_test",
            "test_title",
            "attempt",
            "type",
            "start_time",
            "end_time",
            "total_time",
            "total_score",
            "earned_bonus_point",
            "answer_histories",
        ]

    def get_answer_histories(self, obj):
        """Get answer histories with question and answer details"""
        answer_histories = obj.answer_histories.select_related(
            "receptive_question", "receptive_answer"
        ).all()

        return [
            {
                "id": ah.id,
                "question_id": ah.receptive_question.id,
                "question_number": ah.receptive_question.question_number,
                "question_content": ah.receptive_question.content,
                "selected_answer_id": (
                    ah.receptive_answer.id if ah.receptive_answer else None
                ),
                "user_answer_text": ah.user_answer_text,
                "is_correct": ah.is_correct,
                "question_score": ah.receptive_question.score,
            }
            for ah in answer_histories
        ]
