from rest_framework import serializers
from django.db import transaction

from ..models import (
    ReceptiveTest,
    ReceptivePart,
    ReceptiveQuestion,
    ReceptiveAnswer,
    Test,
)
from ..utils.renumber import renumber_receptive_test
from ..utils.scoring import calculate_scores

# Valid format choices - support both Reading and Listening
VALID_PART_FORMATS = {
    "A": "Listening - Multiple Choice images",
    "B": "Listening - Multiple Choice text (one audio per question)",
    "C": "Listening - Multiple Choice text (one audio for all questions)",
    "D": "Listening - Fill in the blanks",
    "E": "Listening - Matching",
    "F": "Reading - Multiple Choice (short text)",
    "G": "Reading - Multiple Choice (long text)",
    "H": "Reading - Fill in the blanks (multiple choice)",
    "I": "Reading - Fill in the blanks (text)",
    "J": "Reading - Matching",
}

# Listening formats (A-E)
LISTENING_FORMATS = {"A", "B", "C", "D", "E"}
# Reading formats (F-J)
READING_FORMATS = {"F", "G", "H", "I", "J"}

# Valid resource types for receptive tests
VALID_RESOURCE_TYPES = {"image", "audio"}


class ReceptiveTestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating Receptive Tests (Reading & Listening)

    Supports:
    - Reading tests (formats F, G, H, I, J)
    - Listening tests (formats A, B, C, D, E)

    Handles multipart/form-data with:
    - 'data' field: JSON structure defining parts, questions, answers
    """

    data = serializers.JSONField(
        help_text="JSON object with parts, questions, answers structure"
    )

    def validate_data(self, test_data):
        """Validate JSON structure"""
        # Check required fields
        if not isinstance(test_data, dict):
            raise serializers.ValidationError("JSON must be an object/dict")

        parts = test_data.get("parts", [])
        if not isinstance(parts, list):
            raise serializers.ValidationError("'parts' must be a list")

        if not parts:
            raise serializers.ValidationError("'parts' cannot be empty")

        # Basic structure validation
        for idx, part in enumerate(parts):
            if not isinstance(part, dict):
                raise serializers.ValidationError(f"part[{idx}] must be an object")

            if "order" not in part:
                raise serializers.ValidationError(f"part[{idx}] missing 'order' field")

            if "format" not in part:
                raise serializers.ValidationError(f"part[{idx}] missing 'format' field")

            part_format = part.get("format")
            if part_format not in VALID_PART_FORMATS:
                valid_formats = ", ".join(VALID_PART_FORMATS.keys())
                raise serializers.ValidationError(
                    f"part[{idx}] has invalid format '{part_format}'. Valid formats: {valid_formats}"
                )

            # Validate format matches skill (Reading: F-J, Listening: A-E)
            test_id = self.context.get("test_id")
            if test_id:
                try:
                    test = Test.objects.get(pk=test_id)
                    skill = test.skill
                    if skill == "R" and part_format not in READING_FORMATS:
                        valid_str = ", ".join(sorted(READING_FORMATS))
                        raise serializers.ValidationError(
                            f"part[{idx}] has format '{part_format}' which is not valid for Reading skill. "
                            f"Valid Reading formats: {valid_str}"
                        )
                    elif skill == "L" and part_format not in LISTENING_FORMATS:
                        valid_str = ", ".join(sorted(LISTENING_FORMATS))
                        raise serializers.ValidationError(
                            f"part[{idx}] has format '{part_format}' which is not valid for Listening skill. "
                            f"Valid Listening formats: {valid_str}"
                        )
                except Test.DoesNotExist:
                    pass

            # Validate part resources
            part_resources = part.get("resources", {})
            if not isinstance(part_resources, dict):
                raise serializers.ValidationError(
                    f"part[{idx}].resources must be an object/dict"
                )
            invalid_part_resource_types = (
                set(part_resources.keys()) - VALID_RESOURCE_TYPES
            )
            if invalid_part_resource_types:
                invalid_str = ", ".join(sorted(invalid_part_resource_types))
                valid_str = ", ".join(sorted(VALID_RESOURCE_TYPES))
                raise serializers.ValidationError(
                    f"part[{idx}].resources has invalid resource types: {invalid_str}. "
                    f"Allowed types: {valid_str}"
                )

            questions = part.get("questions", [])
            if not isinstance(questions, list):
                raise serializers.ValidationError(
                    f"part[{idx}].questions must be a list"
                )

            for q_idx, question in enumerate(questions):
                if "question_number" not in question:
                    raise serializers.ValidationError(
                        f"part[{idx}].questions[{q_idx}] missing 'question_number'"
                    )

                # Validate question resources
                question_resources = question.get("resources", {})
                if not isinstance(question_resources, dict):
                    raise serializers.ValidationError(
                        f"part[{idx}].questions[{q_idx}].resources must be an object/dict"
                    )
                invalid_question_resource_types = (
                    set(question_resources.keys()) - VALID_RESOURCE_TYPES
                )
                if invalid_question_resource_types:
                    invalid_str = ", ".join(sorted(invalid_question_resource_types))
                    valid_str = ", ".join(sorted(VALID_RESOURCE_TYPES))
                    raise serializers.ValidationError(
                        f"part[{idx}].questions[{q_idx}].resources has invalid resource types: {invalid_str}. "
                        f"Allowed types: {valid_str}"
                    )

                answers = question.get("answers", [])
                if not isinstance(answers, list):
                    raise serializers.ValidationError(
                        f"part[{idx}].questions[{q_idx}].answers must be a list"
                    )

                # Validate option_label
                for a_idx, answer in enumerate(answers):
                    option_label = answer.get("option_label", None)
                    if option_label is not None and len(option_label) != 1:
                        raise serializers.ValidationError(
                            f"part[{idx}].questions[{q_idx}].answers[{a_idx}] option_label must be a single character"
                        )

                    # Validate answer resources
                    answer_resources = answer.get("resources", {})
                    if not isinstance(answer_resources, dict):
                        raise serializers.ValidationError(
                            f"part[{idx}].questions[{q_idx}].answers[{a_idx}].resources must be an object/dict"
                        )
                    invalid_answer_resource_types = (
                        set(answer_resources.keys()) - VALID_RESOURCE_TYPES
                    )
                    if invalid_answer_resource_types:
                        invalid_str = ", ".join(sorted(invalid_answer_resource_types))
                        valid_str = ", ".join(sorted(VALID_RESOURCE_TYPES))
                        raise serializers.ValidationError(
                            f"part[{idx}].questions[{q_idx}].answers[{a_idx}].resources has invalid resource types: {invalid_str}. "
                            f"Allowed types: {valid_str}"
                        )

        # Return the validated JSON structure
        return test_data

    def create(self, validated_data):
        """
        Create receptive test with parts, questions, answers, and resources
        using bulk_create for better performance.

        Flow:
        1. Parse JSON data
        2. Create ReceptiveTest
        3. Bulk create all parts
        4. Bulk create all questions (with part references)
        5. Bulk create all answers (with question references)
        """
        test_id = self.context.get("test_id")

        # JSON data is already parsed by JSONField
        test_data = validated_data.get("data", {})
        if not isinstance(test_data, dict):
            raise serializers.ValidationError({"data": "JSON must be an object/dict"})

        parts_data = test_data.get("parts", [])

        with transaction.atomic():
            # Create ReceptiveTest
            receptive_test = ReceptiveTest.objects.create(test_id=test_id)

            # Prepare parts for bulk create
            parts_to_create = []
            # Store questions data with part index for later reference
            questions_by_part_idx = {}  # {part_idx: [(question_data, score), ...]}

            for part_idx, part_data in enumerate(parts_data):
                part = ReceptivePart(
                    receptive_test=receptive_test,
                    order=part_data.get("order"),
                    format=part_data.get("format"),
                    description=part_data.get("description", ""),
                    content=part_data.get("content", ""),
                    resources=part_data.get("resources", {}),
                    score=0,  # Will be updated after questions are processed
                )
                parts_to_create.append(part)
                questions_by_part_idx[part_idx] = part_data.get("questions", [])

            # Bulk create parts
            created_parts = ReceptivePart.objects.bulk_create(parts_to_create)

            # Prepare questions for bulk create
            questions_to_create = []
            # Store answers data with question index for later reference
            answers_by_question_idx = {}  # {global_question_idx: [answer_data, ...]}
            part_scores = {}  # {part_idx: total_score}
            global_question_idx = 0

            for part_idx, part in enumerate(created_parts):
                part_score = 0
                for question_data in questions_by_part_idx[part_idx]:
                    score = question_data.get("score", 0)
                    question = ReceptiveQuestion(
                        receptive_part=part,
                        question_number=question_data.get("question_number"),
                        content=question_data.get("content", ""),
                        explanation=question_data.get("explanation", ""),
                        score=score,
                        resources=question_data.get("resources", {}),
                    )
                    questions_to_create.append(question)
                    answers_by_question_idx[global_question_idx] = question_data.get(
                        "answers", []
                    )
                    part_score += score
                    global_question_idx += 1

                part_scores[part_idx] = part_score

            # Bulk create questions
            created_questions = ReceptiveQuestion.objects.bulk_create(
                questions_to_create
            )

            # Prepare answers for bulk create
            answers_to_create = []
            for question_idx, question in enumerate(created_questions):
                for answer_data in answers_by_question_idx[question_idx]:
                    answer = ReceptiveAnswer(
                        receptive_question=question,
                        option_label=answer_data.get("option_label", None),
                        answer_text=answer_data.get("answer_text", ""),
                        is_correct=answer_data.get("is_correct", False),
                        resources=answer_data.get("resources", {}),
                    )
                    answers_to_create.append(answer)

            # Bulk create answers
            ReceptiveAnswer.objects.bulk_create(answers_to_create)

            # Renumber parts and questions in ascending order
            renumber_receptive_test(receptive_test)

            # Calculate scores for parts and total score
            calculate_scores(receptive_test)

        return receptive_test
