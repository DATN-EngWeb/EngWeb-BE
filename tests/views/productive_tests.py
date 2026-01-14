from rest_framework import status, generics, serializers
from rest_framework.response import Response

from ..models import Test
from ..serializers.productive_test import ProductiveTestCreateSerializer
from ..permissions import IsTeacher
from accounts.utils import get_or_create_file_storage_uuid

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample,
    inline_serializer,
)


class ProductiveTestCreateView(generics.CreateAPIView):
    """Create ProductiveTest (Writing/Speaking) structure for an existing Test"""

    serializer_class = ProductiveTestCreateSerializer
    permission_classes = [IsTeacher]

    def get_serializer_context(self):
        """Provide extra context for serializer (test_id, user_uuid, files)"""
        context = super().get_serializer_context()
        context.update(
            {
                "test_id": self.kwargs.get("test_id"),
                "user_uuid": get_or_create_file_storage_uuid(self.request.user),
                "files": getattr(self.request, "FILES", {}),
            }
        )
        return context

    @extend_schema(
        summary="Tạo nội dung Productive Test (Writing/Speaking)",
        description=(
            "Tạo cấu trúc Productive Test (Writing/Speaking) cho một bài kiểm tra đã tồn tại.\n\n"
            "**Yêu cầu:**\n"
            "- Bài kiểm tra `test_id` phải tồn tại\n"
            "- Loại bài kiểm tra (type) phải là `P` (Productive)\n"
            "- Chỉ giáo viên (IsTeacher) mới được phép gọi API này\n"
            "- Mỗi bài kiểm tra chỉ có **một** ProductiveTest (nếu đã tồn tại sẽ trả lỗi)\n\n"
            "**Format theo skill:**\n"
            "- Writing (skill=W): Format A-F\n"
            "  - A: Email\n"
            "  - B: Article\n"
            "  - C: Tell a story based on pictures\n"
            "  - D: Essay\n"
            "  - E: Letter\n"
            "  - F: Reviews\n"
            "- Speaking (skill=S): Format G-J\n"
            "  - G: Narrative\n"
            "  - H: Description\n"
            "  - I: Social argument\n"
            "  - J: Reading aloud\n\n"
            "**Body request (JSON):**\n"
            "```json\n"
            "{\n"
            '  "data": {\n'
            '    "format": "E",\n'
            '    "topic": "Describe a memorable trip",\n'
            '    "description": "https://example.com/media/tests/1/content.html",\n'
            '    "min_word": 150,\n'
            '    "glue_text": "Instructions for the test...",\n'
            '    "glue_resources": {\n'
            '      "image": "image_url.png",\n'
            '      "audio": "audio_url.mp3"\n'
            "    }\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "**Các trường trong data:**\n"
            "- `format` (bắt buộc): Định dạng bài test (A-J)\n"
            "- `topic` (tùy chọn): Chủ đề bài test\n"
            "- `description` (tùy chọn): URL mô tả chi tiết\n"
            "- `min_word` (tùy chọn, mặc định 0): Số từ tối thiểu\n"
            "- `glue_text` (tùy chọn): Hướng dẫn cho học viên\n"
            "- `glue_resources` (tùy chọn): Tài nguyên đính kèm (image, audio)"
        ),
        tags=["productive-tests"],
        parameters=[
            OpenApiParameter(
                name="test_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID của bài kiểm tra cần tạo nội dung Productive Test",
            ),
        ],
        request=inline_serializer(
            name="ProductiveTestCreateRequest",
            fields={
                "data": serializers.JSONField(
                    help_text="JSON mô tả cấu trúc Productive Test"
                )
            },
        ),
        examples=[
            OpenApiExample(
                "Writing Test (Letter) example",
                value={
                    "data": {
                        "format": "E",
                        "topic": "Describe a memorable trip you have taken.",
                        "description": "https://example.com/media/tests/1/content.html",
                        "min_word": 150,
                        "glue_text": (
                            "You should write at least 150 words. "
                            "You can use the following points to help you:\n"
                            "- Where you went\n"
                            "- Who you went with\n"
                            "- What you did there\n"
                            "- Why it was memorable"
                        ),
                        "glue_resources": {
                            "image": "glue_image.png",
                            "audio": "glue_audio.mp3",
                        },
                    }
                },
                request_only=True,
            ),
            OpenApiExample(
                "Speaking Test (Narrative) example",
                value={
                    "data": {
                        "format": "G",
                        "topic": "Tell a story about a challenging experience.",
                        "description": "https://example.com/media/tests/2/content.html",
                        "min_word": 0,
                        "glue_text": (
                            "You have 2 minutes to prepare and 3 minutes to speak. "
                            "Include details about:\n"
                            "- What happened\n"
                            "- How you felt\n"
                            "- What you learned"
                        ),
                        "glue_resources": {
                            "image": "prompt_image.png",
                        },
                    }
                },
                request_only=True,
            ),
        ],
        responses={
            201: OpenApiResponse(
                description="Productive Test created successfully",
                response=inline_serializer(
                    name="ProductiveTestCreateResponse",
                    fields={
                        "message": serializers.CharField(help_text="Success message"),
                        "test_id": serializers.IntegerField(
                            help_text="ID bài kiểm tra gốc"
                        ),
                        "format": serializers.CharField(
                            help_text="Format của bài test"
                        ),
                        "topic": serializers.CharField(help_text="Chủ đề bài test"),
                    },
                ),
            ),
            400: OpenApiResponse(
                description="Invalid data or test not eligible for Productive Test",
                response=inline_serializer(
                    name="ProductiveTestCreateErrorResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
            404: OpenApiResponse(
                description="Test not found",
                response=inline_serializer(
                    name="ProductiveTestNotFoundResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        """Handle POST request to create ProductiveTest for a given Test"""

        test_id = kwargs.get("test_id")

        # 1. Validate Test existence
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response(
                {"detail": f"Test with id={test_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Ensure test type is Productive
        if test.type != "P":
            return Response(
                {
                    "detail": "Only Productive tests (type='P') can have Productive Test content. "
                    f"This test has type='{test.type}'.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Ensure ProductiveTest does not already exist
        if hasattr(test, "productivetest"):
            return Response(
                {
                    "detail": "A Productive Test for this test already exists.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Validate and create via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        productive_test = serializer.save()

        response_data = {
            "message": "Productive Test created successfully.",
            "test_id": productive_test.test_id,
            "format": productive_test.format,
            "topic": productive_test.topic,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)
