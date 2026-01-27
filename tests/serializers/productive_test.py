from rest_framework import serializers
from django.db import transaction

from ..models import ProductiveTest, Test

# Valid format choices for Productive tests
VALID_PRODUCTIVE_FORMATS = {
    "A": "Writing - Email",
    "B": "Writing - Article",
    "C": "Writing - Tell a story based on pictures",
    "D": "Writing - Essay",
    "E": "Writing - Letter",
    "F": "Writing - Reviews",
    "G": "Speaking - Narrative",
    "H": "Speaking - Description",
    "I": "Speaking - Social argument",
    "J": "Speaking - Reading aloud",
}

# Writing formats (A-F)
WRITING_FORMATS = {"A", "B", "C", "D", "E", "F"}
# Speaking formats (G-J)
SPEAKING_FORMATS = {"G", "H", "I", "J"}

# Valid resource types for productive tests
VALID_RESOURCE_TYPES = {"image", "audio"}


class ProductiveTestCreateSerializer(serializers.Serializer):
    """
    Serializer for creating Productive Tests (Writing & Speaking)

    Supports:
    - Writing tests (formats A-F)
    - Speaking tests (formats G-J)
    """

    data = serializers.JSONField(help_text="JSON object with productive test structure")

    def validate_data(self, test_data):
        """Validate JSON structure"""
        if not isinstance(test_data, dict):
            raise serializers.ValidationError("JSON must be an object/dict")

        # Validate format (required)
        format_value = test_data.get("format")
        if not format_value:
            raise serializers.ValidationError("'format' field is required")

        if format_value not in VALID_PRODUCTIVE_FORMATS:
            valid_formats = ", ".join(VALID_PRODUCTIVE_FORMATS.keys())
            raise serializers.ValidationError(
                f"Invalid format '{format_value}'. Valid formats: {valid_formats}"
            )

        # Validate format matches skill
        test_id = self.context.get("test_id")
        if test_id:
            try:
                test = Test.objects.get(pk=test_id)
                skill = test.skill

                if skill == "W" and format_value not in WRITING_FORMATS:
                    valid_str = ", ".join(sorted(WRITING_FORMATS))
                    raise serializers.ValidationError(
                        f"Writing skill requires format {valid_str}. Got '{format_value}'."
                    )
                elif skill == "S" and format_value not in SPEAKING_FORMATS:
                    valid_str = ", ".join(sorted(SPEAKING_FORMATS))
                    raise serializers.ValidationError(
                        f"Speaking skill requires format {valid_str}. Got '{format_value}'."
                    )
            except Test.DoesNotExist:
                pass  # Will be handled in view

        # Validate topic (optional but should be string if provided)
        topic = test_data.get("topic", "")
        if not isinstance(topic, str):
            raise serializers.ValidationError("'topic' must be a string")

        # Validate description (optional but should be string if provided)
        description = test_data.get("description", "")
        if not isinstance(description, str):
            raise serializers.ValidationError("'description' must be a string")

        # Validate min_word (optional, default 0)
        min_word = test_data.get("min_word", 0)
        if not isinstance(min_word, int) or min_word < 0:
            raise serializers.ValidationError(
                "'min_word' must be a non-negative integer"
            )

        # Validate glue_text (optional)
        glue_text = test_data.get("glue_text")
        if glue_text is not None and not isinstance(glue_text, str):
            raise serializers.ValidationError("'glue_text' must be a string or null")

        # Validate glue_resources (optional)
        glue_resources = test_data.get("glue_resources", {})
        if not isinstance(glue_resources, dict):
            raise serializers.ValidationError("'glue_resources' must be an object/dict")

        # Validate resource types
        invalid_resource_types = set(glue_resources.keys()) - VALID_RESOURCE_TYPES
        if invalid_resource_types:
            invalid_str = ", ".join(sorted(invalid_resource_types))
            valid_str = ", ".join(sorted(VALID_RESOURCE_TYPES))
            raise serializers.ValidationError(
                f"'glue_resources' has invalid resource types: {invalid_str}. "
                f"Allowed types: {valid_str}"
            )

        return test_data

    @transaction.atomic
    def create(self, validated_data):
        """Create ProductiveTest from validated data"""
        test_id = self.context.get("test_id")
        test_data = validated_data.get("data", {})

        if not isinstance(test_data, dict):
            raise serializers.ValidationError({"data": "JSON must be an object/dict"})

        # Create ProductiveTest
        productive_test = ProductiveTest.objects.create(
            test_id=test_id,
            format=test_data.get("format"),
            topic=test_data.get("topic", ""),
            description=test_data.get("description", ""),
            min_word=test_data.get("min_word", 0),
            glue_text=test_data.get("glue_text"),
            glue_resources=test_data.get("glue_resources", {}),
        )

        return productive_test
