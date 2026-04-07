from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
import django_filters
from datetime import timedelta
from django.utils import timezone


from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
    OpenApiParameter,
)
from rest_framework import serializers as drf_serializers

from .models import ProductiveTestHistory, ReceptiveTestHistory
from .serializers import (
    ProductiveTestHistorySerializer,
    ReceptiveTestHistorySerializer,
    ReceptiveTestHistoryDetailSerializer,
)
from .permissions import IsOwnerOrAdmin, IsStudent
from .filters import ProductiveTestHistoryFilter, ReceptiveTestHistoryFilter


class TestHistoryPagination(PageNumberPagination):
    """Pagination class for test history list APIs."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


def _build_streak_notice(student, previous_last_submitted_date):
    """Return streak notice for submission cases (continued, first-day, same-day)."""
    student.refresh_from_db(fields=["streak_count", "last_submitted_date"])

    today = timezone.localdate()
    if not student.last_submitted_date:
        return None

    current_submitted_date = timezone.localdate(student.last_submitted_date)
    if current_submitted_date != today:
        return None

    # First submission day (no previous submission date).
    if not previous_last_submitted_date:
        return {
            "continued": False,
            "current_streak": student.streak_count,
            "is_streak_lit_today": True,
        }

    previous_date = timezone.localdate(previous_last_submitted_date)
    if previous_date == today - timedelta(days=1):
        return {
            "continued": True,
            "current_streak": student.streak_count,
            "is_streak_lit_today": True,
        }

    # Already submitted today, keep streak and notify with continued=false.
    if previous_date == today:
        return {
            "continued": False,
            "current_streak": student.streak_count,
            "is_streak_lit_today": True,
        }

    # Streak reset or other non-consecutive submission days.
    return {
        "continued": False,
        "current_streak": student.streak_count,
        "is_streak_lit_today": True,
    }


class ProductiveTestHistoryListCreateView(generics.ListCreateAPIView):
    """
    List and Create ProductiveTestHistory records.
    - Students can only see/create their own history
    - Admins can see/create all histories
    """

    serializer_class = ProductiveTestHistorySerializer
    permission_classes = [IsOwnerOrAdmin]  # Default for GET
    pagination_class = TestHistoryPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ProductiveTestHistoryFilter

    def get_permissions(self):
        """Different permissions for GET and POST"""
        if self.request.method == "POST":
            return [IsStudent()]
        return [IsOwnerOrAdmin()]

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        
        # Base queryset based on role
        if user.role == "A":
            queryset = ProductiveTestHistory.objects.select_related(
                "productive_test__test"
            ).order_by("type", "-start_time")
        elif user.role == "S" and hasattr(user, "student"):
            queryset = ProductiveTestHistory.objects.filter(
                student=user.student
            ).select_related("productive_test__test").order_by("type", "-start_time")
        else:
            queryset = ProductiveTestHistory.objects.none()
        
        # Optimize query if is_shared is requested
        if self.request.query_params.get('is_shared') == 'true':
            queryset = queryset.prefetch_related('posts')
        
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create or update ProductiveTestHistory with upsert logic:
        - Draft (D): Override existing draft if any, or create new
        - Submission (S): Convert draft to submission if exists, or create new
        """
        student = request.user.student
        previous_last_submitted_date = student.last_submitted_date
        productive_test_id = request.data.get("productive_test")
        type_value = request.data.get("type", "D")

        # Find existing draft for this student and test
        existing_draft = ProductiveTestHistory.objects.filter(
            student=student, productive_test_id=productive_test_id, type="D"
        ).first()

        if type_value == "D":
            # Draft workflow: Override existing draft or create new
            if existing_draft:
                # Update existing draft
                serializer = self.get_serializer(
                    existing_draft, data=request.data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
                response_data = dict(serializer.data)
                response_data["streak_notice"] = None
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Create new draft
                # Calculate attempt based on submission count
                submission_count = ProductiveTestHistory.objects.filter(
                    student=student, productive_test_id=productive_test_id, type="S"
                ).count()
                attempt = submission_count + 1

                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(student=student, attempt=attempt)
                response_data = dict(serializer.data)
                response_data["streak_notice"] = None
                return Response(response_data, status=status.HTTP_201_CREATED)

        elif type_value == "S":
            # Submission workflow: Convert draft or create new
            if existing_draft:
                # Convert existing draft to submission
                serializer = self.get_serializer(
                    existing_draft, data=request.data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(type="S")
                response_data = dict(serializer.data)
                streak_notice = _build_streak_notice(
                    student, previous_last_submitted_date
                )
                if streak_notice:
                    response_data["streak_notice"] = streak_notice
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Create new submission
                submission_count = ProductiveTestHistory.objects.filter(
                    student=student, productive_test_id=productive_test_id, type="S"
                ).count()
                attempt = submission_count + 1

                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(student=student, attempt=attempt, type="S")
                response_data = dict(serializer.data)
                streak_notice = _build_streak_notice(
                    student, previous_last_submitted_date
                )
                if streak_notice:
                    response_data["streak_notice"] = streak_notice
                return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(
            {"type": "Invalid type. Must be 'D' or 'S'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_serializer_context(self):
        """Add include_is_shared flag to context"""
        context = super().get_serializer_context()
        context['include_is_shared'] = self.request.query_params.get('is_shared') == 'true'
        return context

    def perform_create(self, serializer):
        """Automatically set student from request.user"""
        serializer.save(student=self.request.user.student)

    @extend_schema(
        summary="Lấy danh sách lịch sử làm bài Productive Test",
        description=(
            "API cho phép xem danh sách lịch sử làm bài Productive Test (Writing/Speaking).\n\n"
            "**Quyền truy cập:**\n"
            "- **Học viên (Student)**: Chỉ xem được lịch sử của chính mình\n"
            "- **Admin**: Xem được toàn bộ lịch sử của tất cả học viên\n\n"
            "**Lọc dữ liệu:**\n"
            "- Có thể lọc theo `productive_test` (ID của bài test) thông qua query parameter\n"
            "- Có thể lọc theo `type` (D=Draft, S=Submission) thông qua query parameter\n"
            "- Có thể lọc theo `skill` (`S` hoặc `W`)\n"
            "- Có thể lọc theo `level` (`A1`, `A2`, `B1`, `B2`)\n"
        ),
        tags=["test-histories"],
        parameters=[
            OpenApiParameter(
                name="productive_test",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Lọc theo ID của Productive Test (Writing/Speaking test)",
                required=False,
            ),
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo loại (D=Draft, S=Submission)",
                required=False,
                enum=["D", "S"],
            ),
            OpenApiParameter(
                name="skill",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo kỹ năng của bài test",
                required=False,
                enum=["S", "W"],
            ),
            OpenApiParameter(
                name="level",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo level của bài test",
                required=False,
                enum=["A1", "A2", "B1", "B2"],
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
                name="is_shared",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Bật để kiểm tra xem bài làm đã được chia sẻ lên forum chưa",
                required=False,
                enum=["true", "false"],
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Danh sách lịch sử thành công",
                response=inline_serializer(
                    name="ProductiveHistoryPaginatedResponse",
                    fields={
                        "count": drf_serializers.IntegerField(),
                        "next": drf_serializers.CharField(allow_null=True),
                        "previous": drf_serializers.CharField(allow_null=True),
                        "results": ProductiveTestHistorySerializer(many=True),
                    },
                ),
            ),
            401: OpenApiResponse(
                description="Chưa đăng nhập",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Tạo hoặc cập nhật bài làm (Draft/Submission)",
        description=(
            "API cho phép tạo hoặc cập nhật bản ghi lịch sử làm bài Productive Test.\n\n"
            "**Quyền truy cập:**\n"
            "- **Chỉ học viên (Student)** mới có thể tạo/cập nhật\n"
            "- Admin không được phép tạo\n\n"
            "**Logic Draft (type='D'):**\n"
            "- Nếu đã có draft: Override (cập nhật) draft đó với cùng attempt\n"
            "- Nếu chưa có draft: Tạo draft mới với attempt = (số submission đã nộp) + 1\n"
            "- Chỉ có 1 draft tại một thời điểm cho mỗi bài test\n\n"
            "**Logic Submission (type='S'):**\n"
            "- Nếu đã có draft: Chuyển draft đó thành submission\n"
            "- Nếu chưa có draft: Tạo submission mới với attempt = (số submission đã nộp) + 1\n"
            "- Mỗi submission là 1 lần nộp bài hoàn chỉnh\n\n"
            "**Streak khi submit (type='S'):**\n"
            "- Nếu submit liên tiếp từ hôm qua sang hôm nay: `continued=true`, streak tăng\n"
            "- Nếu lần submit đầu tiên: `continued=false`, `current_streak=1`\n"
            "- Nếu đã submit trong hôm nay: `continued=false`, giữ nguyên streak hiện tại\n"
            "- Nếu bị đứt chuỗi rồi quay lại submit: reset chuỗi về `1`\n"
            "- Response có thêm `streak_notice` gồm `continued` và `current_streak`\n\n"
            "**Lưu ý:**\n"
            "- `student` và `attempt` tự động được set\n"
            "- `type` mặc định là 'D' (Draft) nếu không gửi\n"
            "- `end_time` bắt buộc khi type='S' (Submission)"
        ),
        tags=["test-histories"],
        request=ProductiveTestHistorySerializer,
        examples=[
            OpenApiExample(
                "Tạo hoặc update Draft",
                value={
                    "productive_test": 1,
                    "type": "D",
                    "start_time": "2026-02-06T14:51:37.044Z",
                    "end_time": "2026-02-06T14:52:37.044Z",
                    "total_time": 60,
                    "audio_path": "string",
                    "user_answer_text": "string",
                    "user_note_text": "string",
                    "ai_feedback": "string",
                },
                description="Nếu đã có draft thì sẽ override, nếu chưa có thì tạo mới",
                request_only=True,
            ),
            OpenApiExample(
                "Submit bài làm (chuyển Draft → Submission)",
                value={
                    "productive_test": 1,
                    "type": "S",
                    "start_time": "2026-02-06T14:51:37.044Z",
                    "end_time": "2026-02-06T14:52:37.044Z",
                    "total_time": 60,
                    "audio_path": "string",
                    "user_answer_text": "string",
                    "user_note_text": "string",
                    "ai_feedback": "string",
                },
                description="Nếu có draft thì convert sang submission, nếu không có thì tạo submission mới",
                request_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Cập nhật draft thành công (override existing draft hoặc convert draft → submission)",
                response=ProductiveTestHistorySerializer,
            ),
            201: OpenApiResponse(
                description="Tạo mới draft hoặc submission thành công",
                response=ProductiveTestHistorySerializer,
            ),
            400: OpenApiResponse(
                description="Dữ liệu không hợp lệ (ví dụ: submission không có end_time, type không hợp lệ)",
                response=inline_serializer(
                    name="CreateHistoryError",
                    fields={
                        "productive_test": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "type": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "start_time": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "end_time": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "non_field_errors": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                    },
                ),
            ),
            401: OpenApiResponse(
                description="Chưa đăng nhập",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập (Admin không được phép tạo)",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProductiveTestHistoryRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve a single ProductiveTestHistory record by ID.
    - Students can only retrieve their own history
    - Admins can retrieve any history
    """

    serializer_class = ProductiveTestHistorySerializer
    permission_classes = [IsOwnerOrAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "history_id"

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user

        # Base queryset based on role
        if user.role == "A":
            queryset = ProductiveTestHistory.objects.all()
        elif user.role == "S" and hasattr(user, "student"):
            queryset = ProductiveTestHistory.objects.filter(student=user.student)
        else:
            queryset = ProductiveTestHistory.objects.none()
        
        # Optimize query if is_shared is requested
        if self.request.query_params.get('is_shared') == 'true':
            queryset = queryset.prefetch_related('posts')
        
        return queryset
    
    def get_serializer_context(self):
        """Add include_is_shared flag to context"""
        context = super().get_serializer_context()
        context['include_is_shared'] = self.request.query_params.get('is_shared') == 'true'
        return context

    @extend_schema(
        summary="Lấy chi tiết một bản ghi lịch sử làm bài",
        description=(
            "API cho phép xem chi tiết một bản ghi lịch sử làm bài Productive Test theo ID.\n\n"
            "**Quyền truy cập:**\n"
            "- **Học viên (Student)**: Chỉ xem được lịch sử của chính mình\n"
            "- **Admin**: Xem được bất kỳ lịch sử nào\n\n"
        ),
        tags=["test-histories"],
        parameters=[
            OpenApiParameter(
                name="is_shared",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Bật để kiểm tra xem bài làm đã được chia sẻ lên forum chưa",
                required=False,
                enum=["true", "false"],
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Lấy chi tiết thành công",
                response=ProductiveTestHistorySerializer,
            ),
            401: OpenApiResponse(
                description="Chưa đăng nhập",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập (student cố gắng xem lịch sử của người khác)",
            ),
            404: OpenApiResponse(
                description="Không tìm thấy bản ghi lịch sử với ID này",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ReceptiveTestHistoryListCreateView(generics.ListCreateAPIView):
    """
    List and Create ReceptiveTestHistory records.
    - Students can only see/create their own history
    - Admins can see all histories
    """

    serializer_class = ReceptiveTestHistorySerializer
    permission_classes = [IsOwnerOrAdmin]  # Default for GET
    pagination_class = TestHistoryPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ReceptiveTestHistoryFilter

    def get_permissions(self):
        """Different permissions for GET and POST"""
        if self.request.method == "POST":
            return [IsStudent()]
        return [IsOwnerOrAdmin()]

    def get_serializer_class(self):
        """Use different serializer for list vs create"""
        if self.request.method == "GET":
            return ReceptiveTestHistoryDetailSerializer
        return ReceptiveTestHistorySerializer

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user

        # Admin can see all
        if user.role == "A":
            return (
                ReceptiveTestHistory.objects.select_related(
                    "student__user", "receptive_test__test"
                )
                .prefetch_related(
                    "answer_histories__receptive_question",
                    "answer_histories__receptive_answer",
                )
                .order_by("type", "-start_time")
            )

        # Student can only see their own
        if user.role == "S" and hasattr(user, "student"):
            return (
                ReceptiveTestHistory.objects.filter(student=user.student)
                .select_related("student__user", "receptive_test__test")
                .prefetch_related(
                    "answer_histories__receptive_question",
                    "answer_histories__receptive_answer",
                )
                .order_by("type", "-start_time")
            )

        return ReceptiveTestHistory.objects.none()

    def _save_and_return_response(
        self,
        request,
        instance=None,
        type_value="D",
        previous_last_submitted_date=None,
    ):
        """
        Helper method to save receptive test history and return detailed response.

        Args:
            request: DRF request object
            instance: Existing ReceptiveTestHistory instance (for update) or None (for create)

        Returns:
            Response with detailed history data
        """
        student = request.user.student
        context = {"student": student, "request": request}

        if instance:
            # Update existing instance
            serializer = self.get_serializer(
                instance, data=request.data, partial=True, context=context
            )
            status_code = status.HTTP_200_OK
        else:
            # Create new instance
            serializer = self.get_serializer(data=request.data, context=context)
            status_code = status.HTTP_201_CREATED

        serializer.is_valid(raise_exception=True)
        history = serializer.save()

        # Return detailed response
        detail_serializer = ReceptiveTestHistoryDetailSerializer(history)
        response_data = dict(detail_serializer.data)
        if type_value == "S":
            streak_notice = _build_streak_notice(student, previous_last_submitted_date)
            if streak_notice:
                response_data["streak_notice"] = streak_notice
        else:
            response_data["streak_notice"] = None

        return Response(response_data, status=status_code)

    def create(self, request, *args, **kwargs):
        """
        Create or update ReceptiveTestHistory with upsert logic:
        - Draft (D): Override existing draft if any, or create new
        - Submission (S): Convert draft to submission if exists, or create new
        """
        student = request.user.student
        previous_last_submitted_date = student.last_submitted_date
        receptive_test_id = request.data.get("receptive_test")
        type_value = request.data.get("type", "D")

        # Find existing draft for this student and test
        existing_draft = ReceptiveTestHistory.objects.filter(
            student=student, receptive_test_id=receptive_test_id, type="D"
        ).first()

        if type_value == "D":
            # Draft workflow: Override existing draft or create new
            return self._save_and_return_response(
                request,
                instance=existing_draft,
                type_value=type_value,
                previous_last_submitted_date=previous_last_submitted_date,
            )

        elif type_value == "S":
            # Submission workflow: Convert draft or create new
            return self._save_and_return_response(
                request,
                instance=existing_draft,
                type_value=type_value,
                previous_last_submitted_date=previous_last_submitted_date,
            )

        return Response(
            {"type": "Invalid type. Must be 'D' or 'S'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(
        summary="Lấy danh sách lịch sử làm bài Receptive Test",
        description=(
            "API cho phép xem danh sách lịch sử làm bài Receptive Test (Reading/Listening).\n\n"
            "**Quyền truy cập:**\n"
            "- **Học viên (Student)**: Chỉ xem được lịch sử của chính mình\n"
            "- **Admin**: Xem được toàn bộ lịch sử của tất cả học viên\n\n"
            "**Lọc dữ liệu:**\n"
            "- `receptive_test`: Lọc theo ID của Receptive Test\n"
            "- `type`: Lọc theo loại (D=Draft, S=Submission)\n"
            "- `skill`: Lọc theo kỹ năng (`R` hoặc `L`)\n\n"
            "- `level`: Lọc theo level (`A1`, `A2`, `B1`, `B2`)\n\n"
            "**Response bao gồm:**\n"
            "- Thông tin test history (attempt, times, scores)\n"
            "- Chi tiết tất cả câu trả lời (answer_histories)\n"
            "- Thông tin đúng/sai cho từng câu"
        ),
        tags=["test-histories"],
        parameters=[
            OpenApiParameter(
                name="receptive_test",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Lọc theo ID của Receptive Test (Reading/Listening test)",
                required=False,
            ),
            OpenApiParameter(
                name="type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo loại (D=Draft, S=Submission)",
                required=False,
                enum=["D", "S"],
            ),
            OpenApiParameter(
                name="skill",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo kỹ năng của bài test",
                required=False,
                enum=["R", "L"],
            ),
            OpenApiParameter(
                name="level",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo level của bài test",
                required=False,
                enum=["A1", "A2", "B1", "B2"],
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Số trang hiện tại (mặc định: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Số lượng bản ghi mỗi trang (mặc định 10, tối đa 100)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Danh sách lịch sử thành công (có phân trang)",
                response=inline_serializer(
                    name="ReceptiveHistoryPaginatedResponse",
                    fields={
                        "count": drf_serializers.IntegerField(),
                        "next": drf_serializers.CharField(allow_null=True),
                        "previous": drf_serializers.CharField(allow_null=True),
                        "results": ReceptiveTestHistoryDetailSerializer(many=True),
                    },
                ),
            ),
            401: OpenApiResponse(
                description="Chưa đăng nhập",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Tạo hoặc cập nhật bài làm Receptive Test (Draft/Submission)",
        description=(
            "API cho phép tạo hoặc cập nhật bản ghi lịch sử làm bài Receptive Test với tất cả câu trả lời.\n\n"
            "**Quyền truy cập:**\n"
            "- **Chỉ học viên (Student)** mới có thể tạo/cập nhật\n"
            "- Admin không được phép tạo\n\n"
            "**Logic Draft (type='D'):**\n"
            "- Nếu đã có draft: Override (cập nhật) draft đó với attempt=0\n"
            "- Nếu chưa có draft: Tạo draft mới với attempt=0\n"
            "- Chỉ có 1 draft tại một thời điểm cho mỗi bài test\n"
            "- Draft không tính vào lần làm bài chính thức\n\n"
            "**Logic Submission (type='S'):**\n"
            "- Nếu đã có draft: Chuyển draft đó thành submission (tính điểm, increment attempt)\n"
            "- Nếu chưa có draft: Tạo submission mới với attempt tự động tăng\n"
            "- Mỗi submission là 1 lần nộp bài hoàn chỉnh\n"
            "- Backend tự động tính điểm dựa trên câu trả lời\n\n"
            "**Format câu trả lời (answer_histories):**\n"
            "- Multiple Choice (A,B,C,F,G,H): Gửi `receptive_answer` (ID của đáp án được chọn)\n"
            "- Fill in Blanks (D,I): Gửi `user_answer_text` (text user nhập)\n"
            "- Matching (E,J): Gửi `receptive_answer` (ID của answer mà user nối với question)\n\n"
            "**Tính điểm tự động:**\n"
            "- Backend tự động xác định format của từng câu hỏi\n"
            "- So sánh câu trả lời với đáp án đúng\n"
            "- Tính `total_score` và `is_correct` cho từng câu\n"
            "- Tính `bonus_point` (tổng bonus hiện tại của lần submit)\n"
            "- Tính `earned_bonus_point` (delta được cộng vào điểm của student)\n\n"
            "**Streak khi submit (type='S'):**\n"
            "- Nếu submit liên tiếp từ hôm qua sang hôm nay: `continued=true`, streak tăng\n"
            "- Nếu lần submit đầu tiên: `continued=false`, `current_streak=1`\n"
            "- Nếu đã submit trong hôm nay: `continued=false`, giữ nguyên streak hiện tại\n"
            "- Nếu bị đứt chuỗi rồi quay lại submit: reset chuỗi về `1`\n"
            "- Response có thêm `streak_notice` gồm `continued` và `current_streak`\n\n"
            "**Lưu ý:**\n"
            "- `student` và `attempt` tự động được set\n"
            "- `type` mặc định là 'D' (Draft) nếu không gửi\n"
            "- `end_time` bắt buộc khi type='S' (Submission)\n"
            "- `total_score` tự động tính từ câu trả lời"
        ),
        tags=["test-histories"],
        request=ReceptiveTestHistorySerializer,
        examples=[
            OpenApiExample(
                "Tạo hoặc update Draft",
                value={
                    "receptive_test": 1,
                    "type": "D",
                    "start_time": "2026-02-25T10:00:00Z",
                    "end_time": None,
                    "answer_histories": [
                        {
                            "receptive_question": 1,
                            "receptive_answer": 5,
                        },
                        {
                            "receptive_question": 2,
                            "user_answer_text": "Paris",
                        },
                        {
                            "receptive_question": 3,
                            "receptive_answer": 12,
                        },
                    ],
                },
                description="Lưu draft - nếu đã có draft thì override, nếu chưa có thì tạo mới",
                request_only=True,
            ),
            OpenApiExample(
                "Submit bài làm (chuyển Draft → Submission hoặc tạo mới)",
                value={
                    "receptive_test": 1,
                    "type": "S",
                    "start_time": "2026-02-25T10:00:00Z",
                    "end_time": "2026-02-25T10:45:00Z",
                    "total_time": 2700,
                    "answer_histories": [
                        {
                            "receptive_question": 1,
                            "receptive_answer": 5,
                        },
                        {
                            "receptive_question": 2,
                            "user_answer_text": "Paris",
                        },
                        {
                            "receptive_question": 3,
                            "receptive_answer": 12,
                        },
                    ],
                },
                description=(
                    "Submit bài làm - Backend tự động:\n"
                    "1. Tính điểm cho từng câu\n"
                    "2. Tính tổng điểm\n"
                    "3. Xác định câu nào đúng/sai\n"
                    "4. Tăng attempt number nếu là submission mới"
                ),
                request_only=True,
            ),
            OpenApiExample(
                "Multiple Choice Question",
                value={
                    "receptive_question": 1,
                    "receptive_answer": 5,
                },
                description="Câu hỏi Multiple Choice - gửi ID của answer được chọn",
            ),
            OpenApiExample(
                "Fill in Blanks Question",
                value={
                    "receptive_question": 2,
                    "user_answer_text": "Paris",
                },
                description="Câu hỏi Fill in the Blanks - gửi text user nhập vào",
            ),
            OpenApiExample(
                "Matching Question",
                value={
                    "receptive_question": 3,
                    "receptive_answer": 12,
                },
                description="Câu hỏi Matching - gửi ID của answer mà user nối với question này",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "Cập nhật thành công (override existing draft hoặc convert draft → submission)\n\n"
                    "Response bao gồm:\n"
                    "- Thông tin test history (id, attempt, times, scores)\n"
                    "- Chi tiết tất cả câu trả lời với kết quả đúng/sai"
                ),
                response=ReceptiveTestHistoryDetailSerializer,
            ),
            201: OpenApiResponse(
                description=(
                    "Tạo mới thành công (draft mới hoặc submission mới)\n\n"
                    "Response bao gồm:\n"
                    "- Thông tin test history (id, attempt, times, scores)\n"
                    "- Chi tiết tất cả câu trả lời với kết quả đúng/sai"
                ),
                response=ReceptiveTestHistoryDetailSerializer,
            ),
            400: OpenApiResponse(
                description=(
                    "Dữ liệu không hợp lệ:\n"
                    "- Submission không có end_time\n"
                    "- Type không hợp lệ\n"
                    "- answer_histories không có receptive_answer hoặc user_answer_text\n"
                    "- Question không tồn tại"
                ),
                response=inline_serializer(
                    name="CreateReceptiveHistoryError",
                    fields={
                        "receptive_test": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "type": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "start_time": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "end_time": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "answer_histories": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                        "non_field_errors": drf_serializers.ListField(
                            child=drf_serializers.CharField()
                        ),
                    },
                ),
            ),
            401: OpenApiResponse(
                description="Chưa đăng nhập",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập (Admin không được phép tạo)",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ReceptiveTestHistoryRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve a single ReceptiveTestHistory record by ID.
    - Students can only retrieve their own history
    - Admins can retrieve any history
    """

    serializer_class = ReceptiveTestHistoryDetailSerializer
    permission_classes = [IsOwnerOrAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "history_id"

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user

        # Admin can see all
        if user.role == "A":
            return ReceptiveTestHistory.objects.select_related(
                "student__user", "receptive_test__test"
            ).prefetch_related(
                "answer_histories__receptive_question",
                "answer_histories__receptive_answer",
            )

        # Student can only see their own
        if user.role == "S" and hasattr(user, "student"):
            return (
                ReceptiveTestHistory.objects.filter(student=user.student)
                .select_related("student__user", "receptive_test__test")
                .prefetch_related(
                    "answer_histories__receptive_question",
                    "answer_histories__receptive_answer",
                )
            )

        return ReceptiveTestHistory.objects.none()

    @extend_schema(
        summary="Lấy chi tiết một bản ghi lịch sử làm bài Receptive Test",
        description=(
            "API cho phép xem chi tiết một bản ghi lịch sử làm bài Receptive Test theo ID.\n\n"
            "**Quyền truy cập:**\n"
            "- **Học viên (Student)**: Chỉ xem được lịch sử của chính mình\n"
            "- **Admin**: Xem được bất kỳ lịch sử nào\n\n"
            "**Response bao gồm:**\n"
            "- Thông tin test history (attempt, times, scores, bonus points)\n"
            "- Chi tiết tất cả câu trả lời (answer_histories)\n"
            "- Kết quả đúng/sai cho từng câu\n"
            "- Điểm của từng câu\n"
            "- Nội dung câu hỏi và câu trả lời"
        ),
        tags=["test-histories"],
        responses={
            200: OpenApiResponse(
                description="Lấy chi tiết thành công",
                response=ReceptiveTestHistoryDetailSerializer,
            ),
            401: OpenApiResponse(
                description="Chưa đăng nhập",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập (student cố gắng xem lịch sử của người khác)",
            ),
            404: OpenApiResponse(
                description="Không tìm thấy bản ghi lịch sử với ID này",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
