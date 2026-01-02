from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from ..models import (
    Test,
)
from ..serializers.serializers_reading import ReadingTestCreateSerializer
from ..permissions import IsTeacher
from accounts.utils import get_or_create_file_storage_uuid

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    inline_serializer,
)
from rest_framework import serializers


class ReadingTestCreateView(generics.CreateAPIView):
    """
    Create a Reading Test with parts, questions, and answers using file uploads

    This endpoint handles multipart/form-data requests with:
    - JSON data for test structure (parts, questions, answers) with content as text
    - File uploads for images only

    Flow:
    1. FE calls POST /api/tests/ to create basic Test info → get test_id
    2. FE calls POST /api/tests/reading/{test_id}/ with multipart form-data
       - data: JSON string with test structure (content as text)
       - image_answer_0: Image file for answer 0 (optional)
       - image_answer_1: Image file for answer 1 (optional)
    """

    permission_classes = [IsTeacher]
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        summary="Tạo Reading Test với file upload",
        description=(
            "Tạo nội dung Reading Test bằng multipart/form-data.\n\n"
            "**Cấu trúc request:**\n"
            "```\n"
            "POST /api/tests/reading/{test_id}/\n"
            "Content-Type: multipart/form-data\n"
            "\n"
            "data: {JSON structure}\n"
            "question_image_1.png: <file> (tùy chọn - ảnh cho question)\n"
            "answer_image_1.png: <file> (tùy chọn - ảnh cho answer)\n"
            "```\n\n"
            "**JSON structure (data field):**\n"
            "```json\n"
            "{\n"
            '  "parts": [\n'
            "    {\n"
            '      "order": 1,\n'
            '      "format": "F",\n'
            '      "description": "Mô tả phần này",\n'
            '      "content": "<p>Nội dung HTML của part (tùy chọn)</p>",\n'
            '      "questions": [\n'
            "        {\n"
            '          "question_number": 1,\n'
            '          "content": "Nội dung câu hỏi",\n'
            '          "explanation": "Giải thích đáp án",\n'
            '          "score": 10,\n'
            '          "resources": {"image": "question_image_1.png"},\n'
            '          "answers": [\n'
            "            {\n"
            '              "option_label": "A",\n'
            '              "answer_text": "Lựa chọn A",\n'
            '              "is_correct": true,\n'
            '              "resources": {"image": "answer_image_1.png"}\n'
            "            },\n"
            "            {\n"
            '              "option_label": "B",\n'
            '              "answer_text": "Lựa chọn B",\n'
            '              "is_correct": false,\n'
            '              "resources": {}\n'
            "            }\n"
            "          ]\n"
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n\n"
        ),
        tags=["reading-tests"],
        parameters=[
            OpenApiParameter(
                name="test_id",
                description="ID của test được tạo từ API /api/tests/",
                required=True,
                type=int,
                location="path",
            ),
        ],
        responses={
            201: OpenApiResponse(
                description="Reading test created successfully",
                response={
                    "type": "object",
                    "properties": {
                        "test_id": {"type": "integer"},
                        "total_score": {"type": "integer"},
                        "message": {"type": "string"},
                    },
                },
            ),
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Forbidden - User is not a teacher"),
            404: OpenApiResponse(description="Test not found"),
        },
    )
    def post(self, request, *args, **kwargs):
        test_id = self.kwargs.get("test_id")

        # Verify test exists
        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            return Response(
                {"detail": f"Test with id {test_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if test skill is Reading
        if test.skill != "R":
            return Response(
                {"detail": f"This test is for {test.get_skill_display()}, not Reading!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already has receptive content
        if hasattr(test, "receptivetest"):
            return Response(
                {"detail": "This test already has receptive content"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check authorization - compare by user ID to avoid null/reference issues
        if not test.created_by or test.created_by.user_id != request.user.id:
            return Response(
                {"detail": "You can only add content to your own tests"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get user UUID
        user_uuid = str(get_or_create_file_storage_uuid(request.user))

        serializer = ReadingTestCreateSerializer(
            data=request.data,
            context={
                "request": request,
                "test_id": test_id,
                "user_uuid": user_uuid,
                "files": request.FILES,
            },
        )

        if serializer.is_valid():
            receptive_test = serializer.save()
            return Response(
                {
                    "test_id": receptive_test.test_id,
                    "total_score": receptive_test.total_score,
                    "message": "Reading test created successfully",
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
