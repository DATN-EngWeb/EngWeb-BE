from rest_framework import serializers

from ..models import ReceptiveTest, ReceptivePart, ReceptiveQuestion, ReceptiveAnswer

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

# Valid resource types for receptive tests
VALID_RESOURCE_TYPES = {"image", "audio"}


class ReceptiveTestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating Receptive Tests (Reading & Listening) with file uploads

    Supports:
    - Reading tests (formats F, G, H, I, J)
    - Listening tests (formats A, B, C, D, E)

    Handles multipart/form-data with:
    - JSON data (parts, questions, answers structure)
    - Image files (PNG, JPG, etc.)
    - Audio files (MP3, WAV, etc.)
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

                answers = question.get("answers", [])
                if not isinstance(answers, list):
                    raise serializers.ValidationError(
                        f"part[{idx}].questions[{q_idx}].answers must be a list"
                    )

                # Validate each answer has option_label
                for a_idx, answer in enumerate(answers):
                    if "option_label" not in answer:
                        raise serializers.ValidationError(
                            f"part[{idx}].questions[{q_idx}].answers[{a_idx}] missing 'option_label' field"
                        )

                    option_label = answer.get("option_label")
                    if (
                        not option_label
                        or not isinstance(option_label, str)
                        or len(option_label) != 1
                    ):
                        raise serializers.ValidationError(
                            f"part[{idx}].questions[{q_idx}].answers[{a_idx}] option_label must be a single character"
                        )

                    # Return the validated JSON structure
                    return test_data

    def create(self, validated_data):
        """
        Create receptive test with parts, questions, answers, and resources

        Flow:
        1. Parse JSON data
        2. Create ReceptiveTest
        3. For each part:
           - Save part content (if any)
           - Process part resources (image/audio)
           - For each question:
             - Process question resources
             - For each answer:
               - Process answer resources
        """
        test_id = self.context.get("test_id")
        user_uuid = self.context.get("user_uuid")
        files = self.context.get("files", {})

        # JSON data is already parsed by JSONField
        test_data = validated_data.get("data", {})
        if not isinstance(test_data, dict):
            raise serializers.ValidationError({"data": "JSON must be an object/dict"})

        parts_data = test_data.get("parts", [])

        # Create ReceptiveTest
        receptive_test = ReceptiveTest.objects.create(test_id=test_id)

        # Process parts
        for part_data in parts_data:
            part_order = part_data.get("order")

            # Create part with resources
            part = ReceptivePart.objects.create(
                receptive_test=receptive_test,
                order=part_order,
                format=part_data.get("format"),
                description=part_data.get("description"),
                content=part_data.get("content", ""),
                resources=part_data.get("resources", {}),
            )

            # Process questions
            part_score = 0
            for question_idx, question_data in enumerate(
                part_data.get("questions", [])
            ):
                question = ReceptiveQuestion.objects.create(
                    receptive_part=part,
                    question_number=question_data.get("question_number"),
                    content=question_data.get("content"),
                    explanation=question_data.get("explanation"),
                    score=question_data.get("score", 0),
                    resources=question_data.get("resources", {}),
                )

                part_score += question.score

                # Process answers
                for answer_idx, answer_data in enumerate(
                    question_data.get("answers", [])
                ):

                    answer = ReceptiveAnswer.objects.create(
                        receptive_question=question,
                        option_label=answer_data.get("option_label"),
                        answer_text=answer_data.get("answer_text", ""),
                        is_correct=answer_data.get("is_correct", False),
                        resources=answer_data.get("resources", {}),
                    )

            # Update part score
            part.score = part_score
            part.save()

            # Add to total score
            receptive_test.total_score += part_score

        receptive_test.save()
        return receptive_test
