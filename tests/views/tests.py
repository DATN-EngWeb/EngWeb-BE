from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
import django_filters

from ..models import Test
from ..serializers.serializers_test import TestSerializer
from ..permissions import IsTeacher
from ..filters import TestFilter

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    inline_serializer,
)
from rest_framework import serializers


class TestPagination(PageNumberPagination):
    """
    Pagination class for Tests API
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class TestListCreateView(generics.ListCreateAPIView):
    """
    GET: List all tests with filtering and pagination
    POST: Create a new test (Teacher only)
    """

    queryset = Test.objects.all().order_by("-created_at")
    serializer_class = TestSerializer
    pagination_class = TestPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, OrderingFilter]
    filterset_class = TestFilter
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']

    def get_permissions(self):
        """
        GET: Allow any user
        POST: Only teachers
        """
        if self.request.method == "POST":
            return [IsTeacher()]
        return [permissions.AllowAny()]

    @extend_schema(
        summary="Danh sách bài kiểm tra",
        description=(
            "Lấy danh sách tất cả bài kiểm tra với hỗ trợ lọc, sắp xếp và phân trang.\n\n"
            "**Tham số lọc (Query Parameters):**\n"
            "- `level`: Cấp độ (A1, A2, B1, B2)\n"
            "- `skill`: Kỹ năng - R (Reading), L (Listening), S (Speaking), W (Writing)\n"
            "- `status`: Trạng thái - D (Draft), I (In Review), P (Published), R (Removed)\n"
            "- `page`: Số trang (mặc định: 1)\n"
            "- `page_size`: Số phần tử mỗi trang (mặc định: 10, tối đa: 100)\n\n"
            "**Tham số sắp xếp (Ordering):**\n"
            "- `ordering`: Sắp xếp kết quả\n"
            "  - `created_at` - Ngày tạo (cũ nhất trước)\n"
            "  - `-created_at` - Ngày tạo (mới nhất trước) [mặc định]\n"
            "  - `updated_at` - Ngày cập nhật (cũ nhất trước)\n"
            "  - `-updated_at` - Ngày cập nhật (mới nhất trước)\n"
            "  - `title` - Tên (A-Z)\n"
            "  - `-title` - Tên (Z-A)\n\n"
            "**Ví dụ:**\n"
            "- `/api/tests/?level=B1&skill=R` - Lấy bài Reading cấp B1\n"
            "- `/api/tests/?status=P&page=2&page_size=20` - Trang 2, 20 bài/trang, chỉ Published\n"
            "- `/api/tests/?ordering=title` - Sắp xếp theo tên A-Z\n"
            "- `/api/tests/?ordering=-created_at&skill=R` - Bài Reading, mới nhất trước"
        ),
        tags=["tests"],
        parameters=[
            OpenApiParameter(
                name="level",
                description="Cấp độ (A1, A2, B1, B2)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="skill",
                description="Kỹ năng (R: Reading, L: Listening, S: Speaking, W: Writing)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="status",
                description="Trạng thái (D: Draft, I: In Review, P: Published, R: Removed)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="page",
                description="Số trang (mặc định: 1)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page_size",
                description="Số phần tử mỗi trang (mặc định: 10, tối đa: 100)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="ordering",
                description="Sắp xếp kết quả: created_at, -created_at, updated_at, -updated_at, title, -title",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="List of tests with pagination",
                response={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "example": 25},
                        "next": {
                            "type": "string",
                            "nullable": True,
                            "example": "http://localhost:8000/api/tests/?page=2&page_size=10",
                        },
                        "previous": {
                            "type": "string",
                            "nullable": True,
                            "example": None,
                        },
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer", "example": 1},
                                    "title": {
                                        "type": "string",
                                        "example": "IELTS Reading Test 1",
                                    },
                                    "level": {
                                        "type": "string",
                                        "enum": ["A1", "A2", "B1", "B2"],
                                        "example": "B1",
                                    },
                                    "skill": {
                                        "type": "string",
                                        "enum": ["R", "L", "S", "W"],
                                        "example": "R",
                                    },
                                    "time": {"type": "integer", "example": 60},
                                    "description": {
                                        "type": "string",
                                        "example": "Test description...",
                                    },
                                    "completed_bonus": {
                                        "type": "integer",
                                        "example": 10,
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["D", "I", "P", "R"],
                                        "example": "D",
                                    },
                                    "created_at": {
                                        "type": "string",
                                        "format": "date-time",
                                    },
                                    "updated_at": {
                                        "type": "string",
                                        "format": "date-time",
                                    },
                                    "created_by": {
                                        "type": "integer",
                                        "example": 1,
                                        "nullable": True,
                                    },
                                },
                            },
                        },
                    },
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        # Filter is handled by DjangoFilterBackend + TestFilter
        # Pagination is handled by TestPagination
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Tạo bài kiểm tra mới",
        description=(
            "Tạo một bài kiểm tra mới (chỉ giáo viên).\n\n"
            "**Quyền truy cập:**\n"
            "- **Bắt buộc**: Người dùng phải là giáo viên\n"
            "- Nếu user không phải teacher → 403 Forbidden\n\n"
            "**Trạng thái mặc định:**\n"
            "- Bài kiểm tra mới luôn được tạo với trạng thái `D` (Draft)\n"
            "- `created_by` tự động được set là teacher của người dùng\n\n"
            "**Tham số bắt buộc:**\n"
            "- `title`: Tên bài kiểm tra (không quá 255 ký tự, không được để trống)\n"
            "- `level`: Cấp độ - phải là một trong [A1, A2, B1, B2]\n"
            "- `skill`: Kỹ năng - phải là một trong [R, L, S, W]:\n"
            "  - R: Reading (Đọc)\n"
            "  - L: Listening (Nghe)\n"
            "  - S: Speaking (Nói)\n"
            "  - W: Writing (Viết)\n"
            "- `time`: Thời gian làm bài (phút, tối thiểu 1)\n"
            "- `description`: Mô tả bài kiểm tra (không được để trống)\n\n"
            "**Tham số tùy chọn:**\n"
            "- `completed_bonus`: Điểm thưởng hoàn thành (mặc định: 0, phải >= 0)"
        ),
        tags=["tests"],
        request=inline_serializer(
            name="TestCreateRequest",
            fields={
                "title": serializers.CharField(
                    required=True, help_text="Tên bài kiểm tra"
                ),
                "level": serializers.ChoiceField(
                    choices=["A1", "A2", "B1", "B2"],
                    required=True,
                    help_text="Cấp độ (A1, A2, B1, B2)",
                ),
                "skill": serializers.ChoiceField(
                    choices=["R", "L", "S", "W"],
                    required=True,
                    help_text="Kỹ năng (R: Reading, L: Listening, S: Speaking, W: Writing)",
                ),
                "time": serializers.IntegerField(
                    required=True, help_text="Thời gian làm bài (phút, tối thiểu 1)"
                ),
                "description": serializers.CharField(
                    required=True, help_text="Mô tả bài kiểm tra"
                ),
                "completed_bonus": serializers.IntegerField(
                    required=False,
                    default=0,
                    help_text="Điểm thưởng hoàn thành (mặc định: 0)",
                ),
            },
        ),
        responses={
            201: OpenApiResponse(
                description="Test created successfully",
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "title": {"type": "string", "example": "IELTS Reading Test 1"},
                        "level": {
                            "type": "string",
                            "enum": ["A1", "A2", "B1", "B2"],
                            "example": "B1",
                        },
                        "skill": {
                            "type": "string",
                            "enum": ["R", "L", "S", "W"],
                            "example": "R",
                        },
                        "time": {"type": "integer", "example": 60},
                        "description": {
                            "type": "string",
                            "example": "Test description...",
                        },
                        "completed_bonus": {"type": "integer", "example": 10},
                        "status": {"type": "string", "enum": ["D"], "example": "D"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "created_by": {"type": "integer", "example": 1},
                    },
                    "required": [
                        "id",
                        "title",
                        "level",
                        "skill",
                        "time",
                        "description",
                        "status",
                        "created_at",
                        "updated_at",
                    ],
                },
            ),
            400: OpenApiResponse(
                description="Validation error",
                response={
                    "type": "object",
                    "example": {
                        "title": ["This field is required."],
                        "level": ["Must be one of: B1, B2, A1, A2."],
                    },
                },
            ),
            401: OpenApiResponse(
                description="Unauthorized - User not authenticated",
            ),
            403: OpenApiResponse(
                description="Forbidden - User is not a teacher",
                response={
                    "type": "object",
                    "example": {"detail": "Only teachers can perform this action."},
                },
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
