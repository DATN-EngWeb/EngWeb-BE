from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import OrderingFilter
from rest_framework.exceptions import PermissionDenied
import django_filters

from ..models import Test
from ..serializers.test import TestSerializer
from ..permissions import IsTeacher
from ..filters import TestFilter
from accounts.models import Teacher, Student

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


class TestOverviewListCreateView(generics.ListCreateAPIView):
    """
    GET: List all tests (overview) with filtering and pagination
    POST: Create a new test (Teacher only)
    """

    queryset = (
        Test.objects.all()
        .select_related("created_by__user", "receptive_test", "productive_test")
        .order_by("-created_at")
    )
    serializer_class = TestSerializer
    pagination_class = TestPagination
    filter_backends = [
        django_filters.rest_framework.DjangoFilterBackend,
        OrderingFilter,
    ]
    filterset_class = TestFilter
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-created_at"]

    def get_permissions(self):
        """
        GET: Allow any user
        POST: Only teachers
        """
        if self.request.method == "POST":
            return [IsTeacher()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        """
        Override to handle 'mine' filter parameter and status filtering.
        - mine=true: Filter tests created by current teacher
        - mine=false: Filter tests NOT created by current teacher
        - mine not provided: Show all tests
        Raises PermissionDenied if non-teacher uses mine parameter.
        For non-admin users, exclude tests with status='R' (Removed).
        Raises PermissionDenied if non-admin tries to filter by status='R'.
        """
        queryset = super().get_queryset()
        mine = self.request.query_params.get("mine", "").lower()

        if mine in ["true", "false"]:
            # Check if user is authenticated
            if not self.request.user.is_authenticated:
                raise PermissionDenied(
                    detail="Authentication required to use 'mine' parameter."
                )

            # Check if user is a teacher
            try:
                teacher = Teacher.objects.get(user=self.request.user)
                if mine == "true":
                    queryset = queryset.filter(created_by=teacher)
                else:  # mine == "false"
                    queryset = queryset.exclude(created_by=teacher)
            except Teacher.DoesNotExist:
                raise PermissionDenied(
                    detail="Only teachers can use 'mine' parameter to filter tests."
                )

        # Filter out removed tests for non-admin users
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            queryset = queryset.exclude(status="R")

            # Check if trying to filter by status=R
            status_filter = self.request.query_params.get("status", "")
            if status_filter == "R":
                raise PermissionDenied(
                    detail="Only admin users can filter by status 'R' (Removed)."
                )

        return queryset

    def get_serializer_context(self):
        """
        Override to add progress_status request flag and student to context
        """
        context = super().get_serializer_context()

        # Check if progress_status parameter is requested
        progress_status_param = self.request.query_params.get(
            "progress_status", ""
        ).lower()
        request_progress = progress_status_param == "true"
        context["request_progress_status"] = request_progress

        # If progress_status is requested and user is authenticated, check if user is student
        if request_progress and self.request.user.is_authenticated:
            try:
                student = Student.objects.get(user=self.request.user)
                context["student"] = student
            except Student.DoesNotExist:
                context["student"] = None
        else:
            context["student"] = None

        return context

    @extend_schema(
        summary="Danh sách bài kiểm tra (tổng quan)",
        description=(
            "Lấy danh sách tất cả bài kiểm tra (tổng quan) với hỗ trợ lọc, sắp xếp và phân trang.\n\n"
            "**Lưu ý về quyền truy cập:**\n"
            "- User thường (không phải admin): Không thấy bài kiểm tra có trạng thái 'R' (Removed). Không được phép filter theo status='R'.\n"
            "- Admin: Thấy tất cả bài kiểm tra, bao gồm 'R'. Được phép filter theo status='R'.\n\n"
            "**Tham số lọc (Query Parameters):**\n"
            "- `type`: Loại bài kiểm tra - R (Receptive: Reading/Listening), P (Productive: Speaking/Writing)\n"
            "- `level`: Cấp độ (A1, A2, B1, B2)\n"
            "- `skill`: Kỹ năng - R (Reading), L (Listening), S (Speaking), W (Writing)\n"
            "- `status`: Trạng thái - D (Draft), I (In Review), P (Published), R (Removed)\n"
            "- `year`: Lọc theo năm tạo (VD: 2024, 2025, 2026)\n"
            "- `teacher_name`: Lọc theo tên giáo viên (tìm kiếm không phân biệt hoa thường)\n"
            "- `mine`: Lọc bài kiểm tra theo giáo viên hiện tại - **Yêu cầu đăng nhập và là giáo viên**\n"
            "  - `true`: Lấy các bài test của chính mình\n"
            "  - `false`: Lấy các bài test không phải của mình\n"
            "  - Không truyền: Lấy tất cả bài test\n"
            "- `progress_status`: Hiển thị trạng thái hoàn thành của student (true/false) - **Chỉ áp dụng cho student đã đăng nhập**\n"
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
            "**Lưu ý về tham số `mine`:**\n"
            "- Chỉ giáo viên đã đăng nhập mới được sử dụng tham số `mine` (true hoặc false)\n"
            "- `mine=true`: Lấy các bài test do chính giáo viên hiện tại tạo\n"
            "- `mine=false`: Lấy các bài test do giáo viên khác tạo (không phải của mình)\n"
            "- Không truyền `mine`: Lấy tất cả bài test\n"
            "- Nếu chưa đăng nhập → 403 Forbidden\n"
            "- Nếu không phải giáo viên → 403 Forbidden\n\n"
            "**Lưu ý về tham số `progress_status`:**\n"
            "- Khi `progress_status=true`, API sẽ trả về thêm trường `progress_status` cho mỗi test\n"
            "- Chỉ áp dụng cho student đã đăng nhập\n"
            "- Giá trị trả về:\n"
            "  - `completed`: Student đã submit bài test (có ít nhất 1 submission)\n"
            "  - `draft`: Student chỉ có bản nháp (draft), chưa submit\n"
            "  - `none`: Student chưa làm bài test này\n"
            "- Nếu không truyền `progress_status=true` hoặc user không phải student, trường `progress_status` sẽ không xuất hiện trong response\n\n"
            "**Ví dụ:**\n"
            "- `/api/tests/?type=R` - Lấy tất cả bài Receptive Test (Reading/Listening)\n"
            "- `/api/tests/?type=P&level=B1` - Lấy bài Productive Test cấp B1\n"
            "- `/api/tests/?level=B1&skill=R` - Lấy bài Reading cấp B1\n"
            "- `/api/tests/?status=P&page=2&page_size=20` - Trang 2, 20 bài/trang, chỉ Published\n"
            "- `/api/tests/?year=2026` - Lấy tất cả bài test được tạo năm 2026\n"
            "- `/api/tests/?teacher_name=Nguyen` - Lấy bài test của giáo viên có tên chứa 'Nguyen'\n"
            "- `/api/tests/?ordering=title` - Sắp xếp theo tên A-Z\n"
            "- `/api/tests/?ordering=-created_at&skill=R` - Bài Reading, mới nhất trước\n"
            "- `/api/tests/?mine=true` - Lấy tất cả bài kiểm tra của giáo viên hiện tại\n"
            "- `/api/tests/?mine=false` - Lấy tất cả bài kiểm tra của giáo viên khác (không phải của mình)\n"
            "- `/api/tests/?mine=true&status=D` - Lấy bài Draft của giáo viên hiện tại\n"
            "- `/api/tests/?year=2026&teacher_name=Vu` - Lấy bài test năm 2026 của giáo viên tên 'Vu'\n"
            "- `/api/tests/?progress_status=true` - Lấy danh sách bài test kèm trạng thái hoàn thành của student\n"
            "- `/api/tests/?progress_status=true&level=B1` - Lấy bài test cấp B1 kèm trạng thái hoàn thành"
        ),
        tags=["tests (overview)"],
        parameters=[
            OpenApiParameter(
                name="type",
                description="Loại bài kiểm tra (R: Receptive - Reading/Listening, P: Productive - Speaking/Writing)",
                required=False,
                type=str,
            ),
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
                name="year",
                description="Lọc theo năm tạo (VD: 2024, 2025, 2026)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="teacher_name",
                description="Lọc theo tên giáo viên (tìm kiếm không phân biệt hoa thường, có thể tìm một phần tên)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="mine",
                description=(
                    "Lọc bài kiểm tra theo giáo viên hiện tại (true/false). "
                    "true: Lấy bài test của mình, false: Lấy bài test không phải của mình, không truyền: Lấy tất cả. "
                    "Yêu cầu: Phải đăng nhập và là giáo viên. "
                    "Nếu không thỏa điều kiện sẽ trả về 403."
                ),
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="progress_status",
                description=(
                    "Hiển thị trạng thái hoàn thành của student (true/false). "
                    "Chỉ áp dụng cho student đã đăng nhập. "
                    "Trả về: completed (đã submit), draft (chỉ có nháp), none (chưa làm). "
                    "Nếu không truyền tham số này hoặc user không phải student, trường progress_status sẽ không xuất hiện trong response."
                ),
                required=False,
                type=bool,
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
            200: TestSerializer(many=True),
            403: OpenApiResponse(
                description="Forbidden - Using mine=true but not a teacher or not authenticated",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {
                            "type": "string",
                            "example": "Only teachers can use 'mine' parameter to filter their own tests.",
                        },
                    },
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        # Filter is handled by DjangoFilterBackend + TestFilter
        # Pagination is handled by TestPagination
        # 'mine' filter is handled in get_queryset()
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Tạo bài kiểm tra mới (thông tin tổng quan)",
        description=(
            "Tạo một bài kiểm tra mới (chỉ giáo viên).\n\n"
            "**Quyền truy cập:**\n"
            "- **Bắt buộc**: Người dùng phải là giáo viên\n"
            "- Nếu user không phải teacher → 403 Forbidden\n\n"
            "**Trạng thái mặc định:**\n"
            "- Bài kiểm tra được tạo với trạng thái mặc định là `D` (Draft)\n"
            "- `created_by` tự động được set là teacher của người dùng\n\n"
            "**Tham số bắt buộc:**\n"
            "- `title`: Tên bài kiểm tra (không quá 255 ký tự, không được để trống)\n"
            "- `type`: Loại bài kiểm tra - phải là một trong [R, P]:\n"
            "  - R: Receptive (dành cho Reading/Listening)\n"
            "  - P: Productive (dành cho Speaking/Writing)\n"
            "- `level`: Cấp độ - phải là một trong [A1, A2, B1, B2]\n"
            "- `skill`: Kỹ năng - phải là một trong [R, L, S, W]:\n"
            "  - R: Reading (Đọc) - yêu cầu type=R\n"
            "  - L: Listening (Nghe) - yêu cầu type=R\n"
            "  - S: Speaking (Nói) - yêu cầu type=P\n"
            "  - W: Writing (Viết) - yêu cầu type=P\n"
            "- `time`: Thời gian làm bài (phút, tối thiểu 1)\n"
            "- `description`: Mô tả bài kiểm tra (không được để trống)\n\n"
            "**Tham số tùy chọn:**\n"
            "- `status`: Trạng thái - D (Draft), I (In Review), P (Published) (mặc định: D)\n\n"
            "**Lưu ý:**\n"
            "- `type` và `skill` phải tương thích:\n"
            "  - type=R chỉ dùng với skill=R hoặc skill=L\n"
            "  - type=P chỉ dùng với skill=S hoặc skill=W"
        ),
        tags=["tests (overview)"],
        request=inline_serializer(
            name="TestCreateRequest",
            fields={
                "title": serializers.CharField(
                    required=True, help_text="Tên bài kiểm tra"
                ),
                "type": serializers.ChoiceField(
                    choices=["R", "P"],
                    required=True,
                    help_text="Loại bài kiểm tra (R: Receptive - Reading/Listening, P: Productive - Speaking/Writing)",
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
                "status": serializers.ChoiceField(
                    choices=["D", "I", "P"],
                    required=False,
                    default="D",
                    help_text=(
                        "Trạng thái (D: Draft, I: In Review, P: Published). "
                        "Nếu không gửi sẽ mặc định là D."
                    ),
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
                        "type": {
                            "type": "string",
                            "enum": ["R", "P"],
                            "example": "R",
                            "description": "R: Receptive, P: Productive",
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
                        "status": {
                            "type": "string",
                            "enum": ["D", "I", "P"],
                            "example": "D",
                        },
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "created_by": {"type": "integer", "example": 1},
                    },
                    "required": [
                        "id",
                        "title",
                        "type",
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
