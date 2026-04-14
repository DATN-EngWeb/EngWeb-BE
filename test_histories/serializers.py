from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Max
from .models import ProductiveTestHistory, ReceptiveTestHistory, ReceptiveAnswerHistory
from accounts.models import Student
from tests.models import (
    ProductiveTest,
    ReceptiveTest,
    ReceptiveQuestion,
    ReceptiveAnswer,
)
from user_progress.models import CompletedBonus, EXPBonusRule
from user_progress.utils import sync_student_level_from_cumulative_point
import json


def _update_student_streak_for_submission(student_id):
    """Update student's streak metrics when a submission is made."""
    now = timezone.now()
    today = timezone.localdate(now)

    student = Student.objects.select_for_update().get(pk=student_id)

    if student.last_submitted_date:
        last_submitted_date = timezone.localdate(student.last_submitted_date)

        if last_submitted_date == today:
            new_streak_count = student.streak_count
        elif last_submitted_date == today - timedelta(days=1):
            new_streak_count = student.streak_count + 1
        else:
            new_streak_count = 1
    else:
        new_streak_count = 1

    student.streak_count = new_streak_count
    student.max_streak = max(student.max_streak, new_streak_count)
    student.last_submitted_date = now
    student.save(update_fields=["streak_count", "max_streak", "last_submitted_date"])


class BaseSubmissionHistorySerializer(serializers.ModelSerializer):
    """Shared validation for draft/submission history serializers."""

    submitted_type_error = {"type": "Submitted history cannot be updated."}
    required_end_time_error = {"end_time": "End time is required for submissions."}

    def validate(self, attrs):
        if self.instance and self.instance.type == "S":
            raise serializers.ValidationError(self.submitted_type_error)

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

        type_value = attrs.get("type", self.instance.type if self.instance else "D")
        if type_value == "S" and not (end_time or (self.instance and self.instance.end_time)):
            raise serializers.ValidationError(self.required_end_time_error)

        return attrs


class ProductiveTestHistorySerializer(BaseSubmissionHistorySerializer):
    """Serializer for list and create ProductiveTestHistory"""

    test_title = serializers.CharField(source="productive_test.test.title", read_only=True)
    level = serializers.CharField(source="productive_test.test.level", read_only=True)
    ai_feedback = serializers.SerializerMethodField()
    is_shared = serializers.SerializerMethodField()
    post_id = serializers.SerializerMethodField()

    class Meta:
        model = ProductiveTestHistory
        fields = [
            "id",
            "student",
            "productive_test",
            "test_title",
            "level",
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
        attrs = super().validate(attrs)

        # For create operations
        if not self.instance:
            productive_test = attrs.get("productive_test")

            # Check if productive_test exists
            if not ProductiveTest.objects.filter(pk=productive_test.pk).exists():
                raise serializers.ValidationError(
                    {"productive_test": "Productive test does not exist."}
                )

        return attrs

    @staticmethod
    def _calculate_productive_bonus_point(productive_test):
        completed_bonus = CompletedBonus.objects.get(
            skill=productive_test.test.skill,
            level=productive_test.test.level,
        )
        return int(
            Decimal(str(completed_bonus.completed_bonus)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    def _apply_submission_exp(self, productive_test_history):
        if productive_test_history.type != "S":
            productive_test_history.earned_bonus_point = 0
            productive_test_history.save(update_fields=["earned_bonus_point"])
            return productive_test_history.earned_bonus_point

        _update_student_streak_for_submission(productive_test_history.student_id)

        has_previous_submission = ProductiveTestHistory.objects.filter(
            student=productive_test_history.student,
            productive_test=productive_test_history.productive_test,
            type="S",
        ).exclude(pk=productive_test_history.pk).exists()

        if has_previous_submission:
            productive_test_history.earned_bonus_point = 0
            productive_test_history.save(update_fields=["earned_bonus_point"])
            productive_test_history._level_notice = None
            return productive_test_history.earned_bonus_point

        bonus_point = self._calculate_productive_bonus_point(
            productive_test_history.productive_test
        )
        productive_test_history.earned_bonus_point = bonus_point
        productive_test_history.save(update_fields=["earned_bonus_point"])

        # Update student's points only if this is the first submission for this test
        if bonus_point:
            Student.objects.filter(pk=productive_test_history.student_id).update(
                cumulative_point=F("cumulative_point") + bonus_point,
                weekly_point=F("weekly_point") + bonus_point,
            )
            productive_test_history._level_notice = (
                sync_student_level_from_cumulative_point(productive_test_history.student_id)
            )
        else:
            productive_test_history._level_notice = None

        return productive_test_history.earned_bonus_point

    @transaction.atomic
    def create(self, validated_data):
        productive_test_history = super().create(validated_data)
        self._apply_submission_exp(productive_test_history)
        return productive_test_history

    @transaction.atomic
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        self._apply_submission_exp(instance)
        return instance


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


class ReceptiveTestHistorySerializer(BaseSubmissionHistorySerializer):
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
            "bonus_point",
            "earned_bonus_point",
            "answer_histories",
        ]
        read_only_fields = [
            "id",
            "student",
            "attempt",
            "total_score",
            "bonus_point",
            "earned_bonus_point",
        ]

    def validate(self, attrs):
        """Validate the data"""
        attrs = super().validate(attrs)

        # For create operations, check if receptive_test exists
        if not self.instance:
            receptive_test = attrs.get("receptive_test")
            if not ReceptiveTest.objects.filter(pk=receptive_test.pk).exists():
                raise serializers.ValidationError(
                    {"receptive_test": "Receptive test does not exist."}
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

    @staticmethod
    def _get_exp_bonus_rule(completion_percentage):
        if completion_percentage >= 100:
            return EXPBonusRule.objects.get(max_percentage=100)

        return EXPBonusRule.objects.get(
            min_percentage__lte=completion_percentage,
            max_percentage__gt=completion_percentage,
        )

    @staticmethod
    def _calculate_bonus_point(receptive_test, total_score):
        """
        Calculate bonus points based on completion percentage and bonus rules
        Returns: (bonus_point, completion_percentage, completed_bonus, exp_rule)
        """
        max_score = receptive_test.total_score or 0
        if max_score <= 0:
            return 0, 0.0, 0, None

        completion_percentage = (total_score / max_score) * 100
        exp_rule = ReceptiveTestHistorySerializer._get_exp_bonus_rule(
            completion_percentage
        )

        completed_bonus = CompletedBonus.objects.get(
            skill=receptive_test.test.skill,
            level=receptive_test.test.level,
        )

        exp_earned = (
            Decimal(str(completed_bonus.completed_bonus))
            * Decimal(str(exp_rule.exp_percentage))
            / Decimal("100")
        )
        bonus_point = int(
            exp_earned.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

        return bonus_point, round(completion_percentage, 2), completed_bonus, exp_rule

    def _build_answer_history_objects(self, receptive_test_history, answer_histories_data):
        total_score = 0
        answer_history_objects = []

        for answer_data in answer_histories_data:
            question = answer_data["receptive_question"]
            selected_answer = answer_data.get("receptive_answer")
            user_text = answer_data.get("user_answer_text")

            is_correct, score = self._calculate_answer_score(
                question, selected_answer, user_text
            )

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

        return total_score, answer_history_objects

    def _persist_answer_histories(self, receptive_test_history, answer_histories_data):
        if not answer_histories_data:
            return 0

        total_score, answer_history_objects = self._build_answer_history_objects(
            receptive_test_history, answer_histories_data
        )

        if answer_history_objects:
            ReceptiveAnswerHistory.objects.bulk_create(answer_history_objects)

        receptive_test_history.total_score = total_score
        receptive_test_history.save(update_fields=["total_score"])

        return total_score

    def _apply_bonus_points(self, receptive_test_history, previous_bonus_point=0):
        if receptive_test_history.type != "S":
            receptive_test_history.bonus_point = 0
            receptive_test_history.earned_bonus_point = 0
            receptive_test_history.save(update_fields=["bonus_point", "earned_bonus_point"])
            return receptive_test_history.bonus_point, receptive_test_history.earned_bonus_point

        _update_student_streak_for_submission(receptive_test_history.student_id)

        bonus_point, _, _, _ = self._calculate_bonus_point(
            receptive_test_history.receptive_test,
            receptive_test_history.total_score or 0,
        )

        receptive_test_history.bonus_point = bonus_point
        # Only award positive improvement; do not subtract points on worse attempts.
        receptive_test_history.earned_bonus_point = max(
            0, bonus_point - previous_bonus_point
        )
        receptive_test_history.save(update_fields=["bonus_point", "earned_bonus_point"])

        delta = receptive_test_history.earned_bonus_point
        
        # Update student's points based on the delta of earned bonus points compared to previous best submission
        if delta:
            Student.objects.filter(pk=receptive_test_history.student_id).update(
                cumulative_point=F("cumulative_point") + delta,
                weekly_point=F("weekly_point") + delta,
            )
            receptive_test_history._level_notice = (
                sync_student_level_from_cumulative_point(receptive_test_history.student_id)
            )
        else:
            receptive_test_history._level_notice = None

        return receptive_test_history.bonus_point, receptive_test_history.earned_bonus_point

    def _get_previous_submission_bonus(self, receptive_test_history):
        best_bonus = (
            ReceptiveTestHistory.objects.filter(
                student=receptive_test_history.student,
                receptive_test=receptive_test_history.receptive_test,
                type="S",
            )
            .exclude(pk=receptive_test_history.pk)
            .aggregate(best_bonus=Max("bonus_point"))
        )

        return best_bonus["best_bonus"] or 0

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

        self._persist_answer_histories(receptive_test_history, answer_histories_data)

        if receptive_test_history.type == "S":
            previous_bonus_point = self._get_previous_submission_bonus(receptive_test_history)
            self._apply_bonus_points(receptive_test_history, previous_bonus_point=previous_bonus_point)
        else:
            self._apply_bonus_points(receptive_test_history, previous_bonus_point=0)

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
            instance.answer_histories.all().delete()
            self._persist_answer_histories(instance, answer_histories_data)

        if instance.type == "S":
            bonus_before_save = self._get_previous_submission_bonus(instance)
            self._apply_bonus_points(instance, previous_bonus_point=bonus_before_save)
        else:
            self._apply_bonus_points(instance, previous_bonus_point=0)

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
    level = serializers.CharField(
        source="receptive_test.test.level", read_only=True
    )
    completion_percentage = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    feedback_message = serializers.SerializerMethodField()

    class Meta:
        model = ReceptiveTestHistory
        fields = [
            "id",
            "student",
            "student_username",
            "receptive_test",
            "test_title",
            "level",
            "attempt",
            "type",
            "start_time",
            "end_time",
            "total_time",
            "total_score",
            "completion_percentage",
            "bonus_point",
            "earned_bonus_point",
            "rating",
            "feedback_message",
            "answer_histories",
        ]

    @staticmethod
    def _resolve_exp_rule(completion_percentage):
        if completion_percentage is None:
            return None

        try:
            if completion_percentage >= 100:
                return EXPBonusRule.objects.get(max_percentage=100)

            return EXPBonusRule.objects.get(
                min_percentage__lte=completion_percentage,
                max_percentage__gt=completion_percentage,
            )
        except (EXPBonusRule.DoesNotExist, EXPBonusRule.MultipleObjectsReturned):
            return None

    def get_completion_percentage(self, obj):
        max_score = obj.receptive_test.total_score or 0
        achieved_score = obj.total_score or 0

        if max_score <= 0:
            return 0.0

        return round((achieved_score / max_score) * 100, 2)

    def get_rating(self, obj):
        if obj.type != "S":
            return None

        exp_rule = self._resolve_exp_rule(self.get_completion_percentage(obj))
        return exp_rule.rating if exp_rule else None

    def get_feedback_message(self, obj):
        if obj.type != "S":
            return None

        exp_rule = self._resolve_exp_rule(self.get_completion_percentage(obj))
        return exp_rule.feedback_message if exp_rule else None

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
