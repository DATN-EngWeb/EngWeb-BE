from rest_framework import status, generics, serializers
from rest_framework.response import Response
from rest_framework.parsers import BaseParser
from rest_framework.views import APIView
import io

from django.http.request import HttpRequest
from django.http.multipartparser import MultiPartParser
from django.core.files.uploadhandler import MemoryFileUploadHandler

from ..models import Test
from ..serializers.serializers_receptive_test import ReceptiveTestCreateSerializer
from ..permissions import IsTeacher
from accounts.utils import get_or_create_file_storage_uuid

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample,
    inline_serializer,
)


class ReceptiveTestCreateView(generics.CreateAPIView):
    """Create ReceptiveTest (Reading/Listening) structure for an existing Test"""

    serializer_class = ReceptiveTestCreateSerializer
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
        summary="Tạo nội dung Receptive Test (Reading/Listening)",
        description=(
            "Tạo cấu trúc Receptive Test (Reading/Listening) cho một bài kiểm tra đã tồn tại.\n\n"
            "**Yêu cầu:**\n"
            "- Bài kiểm tra `test_id` phải tồn tại\n"
            "- Kỹ năng của bài kiểm tra phải là `R` (Reading) hoặc `L` (Listening)\n"
            "- Chỉ giáo viên (IsTeacher) mới được phép gọi API này\n"
            "- Mỗi bài kiểm tra chỉ có **một** ReceptiveTest (nếu đã tồn tại sẽ trả lỗi)\n\n"
            "**Body request (JSON):**\n"
            "- Trường duy nhất: `data` chứa JSON mô tả cấu trúc parts/questions/answers.\n"
            "- Ví dụ nội dung `data`:\n\n"
            "```json\n"
            "{\n"
            '  "parts": [\n'
            "    {\n"
            '      "order": 1,\n'
            '      "format": "F",\n'
            '      "description": "Mô tả phần này",\n'
            '      "content": "...url/url/url",\n'
            '      "questions": [\n'
            "        {\n"
            '          "question_number": 1,\n'
            '          "content": "Nội dung câu hỏi",\n'
            '          "explanation": "Giải thích đáp án",\n'
            '          "score": 10,\n'
            '          "resources": {"image": "...url/url/url"},\n'
            '          "answers": [\n'
            "            {\n"
            '              "option_label": "A",\n'
            '              "answer_text": "Lựa chọn A",\n'
            '              "is_correct": true,\n'
            '              "resources": {"image": "...url/url/url"}\n'
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
        ),
        tags=["receptive-tests"],
        parameters=[
            OpenApiParameter(
                name="test_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID của bài kiểm tra cần tạo nội dung Receptive Test",
            ),
        ],
        request=inline_serializer(
            name="ReceptiveTestCreateRequest",
            fields={
                "data": serializers.JSONField(
                    help_text=(
                        "JSON mô tả cấu trúc Receptive Test (parts, questions, answers). "
                        "Ví dụ: xem phần mô tả ở trên."
                    ),
                )
            },
        ),
        examples=[
            OpenApiExample(
                "ReceptiveTestCreate example",
                value={
                    "data": {
                        "parts": [
                            {
                                "order": 1,
                                "format": "F",
                                "description": "Description of this part",
                                "content": "https://example.com/media/tests/1/part1/content.html",
                                "questions": [
                                    {
                                        "question_number": 1,
                                        "content": "Question content",
                                        "explanation": "Explanation for the correct answer",
                                        "score": 10,
                                        "resources": {
                                            "image": "https://example.com/media/tests/1/part1/image1.png"
                                        },
                                        "answers": [
                                            {
                                                "option_label": "A",
                                                "answer_text": "Option A",
                                                "is_correct": True,
                                                "resources": {},
                                            },
                                            {
                                                "option_label": "B",
                                                "answer_text": "Option B",
                                                "is_correct": False,
                                                "resources": {},
                                            },
                                        ],
                                    }
                                ],
                            },
                            {
                                "order": 2,
                                "format": "F",
                                "description": "Description of this part",
                                "content": "https://example.com/media/tests/1/part2/content.html",
                                "questions": [
                                    {
                                        "question_number": 1,
                                        "content": "Question content",
                                        "explanation": "Explanation for the correct answer",
                                        "score": 10,
                                        "resources": {
                                            "image": "https://example.com/media/tests/1/part2/image2.png"
                                        },
                                        "answers": [
                                            {
                                                "option_label": "A",
                                                "answer_text": "Option A",
                                                "is_correct": True,
                                                "resources": {
                                                    "image": "https://example.com/media/tests/1/part2/answerA_image.png"
                                                },
                                            },
                                            {
                                                "option_label": "B",
                                                "answer_text": "Option B",
                                                "is_correct": False,
                                                "resources": {},
                                            },
                                        ],
                                    }
                                ],
                            },
                        ]
                    }
                },
            )
        ],
        responses={
            201: OpenApiResponse(
                description="Receptive Test created successfully",
                response=inline_serializer(
                    name="ReceptiveTestCreateResponse",
                    fields={
                        "message": serializers.CharField(help_text="Success message"),
                        "test_id": serializers.IntegerField(
                            help_text="ID bài kiểm tra gốc"
                        ),
                        "total_score": serializers.IntegerField(
                            help_text="Tổng điểm của toàn bộ Receptive Test"
                        ),
                        "parts_count": serializers.IntegerField(
                            help_text="Số lượng parts đã tạo"
                        ),
                    },
                ),
            ),
            400: OpenApiResponse(
                description="Invalid data or test not eligible for Receptive Test",
                response=inline_serializer(
                    name="ReceptiveTestCreateErrorResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
            404: OpenApiResponse(
                description="Test not found",
                response=inline_serializer(
                    name="ReceptiveTestNotFoundResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        """Handle POST request to create ReceptiveTest for a given Test"""

        test_id = kwargs.get("test_id")

        # 1. Validate Test existence
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response(
                {"detail": f"Test with id={test_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Ensure skill is Reading or Listening
        if test.skill not in ("R", "L"):
            return Response(
                {
                    "detail": "Only Reading (R) and Listening (L) tests can have a Receptive Test.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Ensure ReceptiveTest does not already exist
        if hasattr(test, "receptivetest"):
            return Response(
                {
                    "detail": "A Receptive Test for this test already exists.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Validate and create via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receptive_test = serializer.save()

        response_data = {
            "message": "Receptive Test created successfully.",
            "test_id": receptive_test.test_id,
            "total_score": receptive_test.total_score,
            "parts_count": receptive_test.receptive_parts.count(),
        }

        return Response(response_data, status=status.HTTP_201_CREATED)
