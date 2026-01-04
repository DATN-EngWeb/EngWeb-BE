import json
from rest_framework import serializers

from ..models import ReceptiveTest, ReceptivePart, ReceptiveQuestion, ReceptiveAnswer
from ..utils.upload_file import save_html_content, save_uploaded_file

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

    data = serializers.CharField(
        help_text="JSON string with parts, questions, answers structure (content is text, not file)"
    )

    def validate_data(self, value):
        """Validate JSON format and structure"""
        try:
            test_data = json.loads(value)
        except json.JSONDecodeError as e:
            raise serializers.ValidationError(f"Invalid JSON format: {str(e)}")

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

        return value

    def _process_resources(self, resources_data, files, user_uuid, test_id, part_order):
        """
        Process resources for a part/question/answer

        Args:
            resources_data: Dict of {resource_type: file_name}
                           e.g., {"image": "question_1.png", "audio": "q1_audio.mp3"}
            files: Dict of available files from request
            user_uuid: User's UUID for storage
            test_id: Test ID
            part_order: Part order number

        Returns:
            Dict of {resource_type: file_path}
                    e.g., {"image": "media/receptive_test/uuid/test_1/part_1/...", ...}
        """
        processed_resources = {}

        if not isinstance(resources_data, dict):
            return processed_resources

        for resource_type, file_name in resources_data.items():
            # Validate resource type
            if resource_type not in VALID_RESOURCE_TYPES:
                continue  # Skip invalid types

            # Check if file exists in uploaded files
            if not file_name or file_name not in files:
                continue

            # Save the file (both image and audio supported)
            file_obj = files[file_name]
            file_path = save_uploaded_file(file_obj, user_uuid, test_id, part_order)
            processed_resources[resource_type] = file_path

        return processed_resources

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

        # Parse JSON data
        try:
            test_data = json.loads(validated_data.get("data", "{}"))
        except json.JSONDecodeError:
            raise serializers.ValidationError({"data": "Invalid JSON format"})

        parts_data = test_data.get("parts", [])

        # Create ReceptiveTest
        receptive_test = ReceptiveTest.objects.create(test_id=test_id)

        # Process parts
        for part_data in parts_data:
            part_order = part_data.get("order")

            # Save part content (if any)
            content_path = None
            content_text = part_data.get("content")
            if content_text:
                content_path = save_html_content(
                    content_text, user_uuid, test_id, part_order
                )

            # Process part resources (image/audio)
            part_resources = self._process_resources(
                part_data.get("resources", {}), files, user_uuid, test_id, part_order
            )

            # Create part with resources
            part = ReceptivePart.objects.create(
                receptive_test=receptive_test,
                order=part_order,
                format=part_data.get("format"),
                description=part_data.get("description"),
                content=content_path,
                resources=part_resources,
            )

            # Process questions
            part_score = 0
            for question_idx, question_data in enumerate(
                part_data.get("questions", [])
            ):
                # Process question resources (image/audio)
                question_resources = self._process_resources(
                    question_data.get("resources", {}),
                    files,
                    user_uuid,
                    test_id,
                    part_order,
                )

                question = ReceptiveQuestion.objects.create(
                    receptive_part=part,
                    question_number=question_data.get("question_number"),
                    content=question_data.get("content"),
                    explanation=question_data.get("explanation"),
                    score=question_data.get("score", 0),
                    resources=question_resources,
                )

                part_score += question.score

                # Process answers
                for answer_idx, answer_data in enumerate(
                    question_data.get("answers", [])
                ):
                    # Process answer resources (image/audio)
                    answer_resources = self._process_resources(
                        answer_data.get("resources", {}),
                        files,
                        user_uuid,
                        test_id,
                        part_order,
                    )

                    answer = ReceptiveAnswer.objects.create(
                        receptive_question=question,
                        option_label=answer_data.get("option_label"),
                        answer_text=answer_data.get("answer_text", ""),
                        is_correct=answer_data.get("is_correct", False),
                        resources=answer_resources,
                    )

            # Update part score
            part.score = part_score
            part.save()

            # Add to total score
            receptive_test.total_score += part_score

        receptive_test.save()
        return receptive_test
