from rest_framework import generics, status
from rest_framework.response import Response
import django_filters


from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
    OpenApiParameter,
)
from rest_framework import serializers as drf_serializers

from .models import ProductiveTestHistory
from .serializers import ProductiveTestHistorySerializer
from .permissions import IsOwnerOrAdmin, IsStudent
from .filters import ProductiveTestHistoryFilter


class ProductiveTestHistoryListCreateView(generics.ListCreateAPIView):
    """
    List and Create ProductiveTestHistory records.
    - Students can only see/create their own history
    - Admins can see/create all histories
    """

    serializer_class = ProductiveTestHistorySerializer
    permission_classes = [IsOwnerOrAdmin]  # Default for GET
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

        # Admin can see all
        if user.role == "A":
            return ProductiveTestHistory.objects.order_by("type", "-start_time")

        # Student can only see their own
        if user.role == "S" and hasattr(user, "student"):
            return ProductiveTestHistory.objects.filter(student=user.student).order_by(
                "type", "-start_time"
            )

        return ProductiveTestHistory.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Create or update ProductiveTestHistory with upsert logic:
        - Draft (D): Override existing draft if any, or create new
        - Submission (S): Convert draft to submission if exists, or create new
        """
        student = request.user.student
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
                return Response(serializer.data, status=status.HTTP_200_OK)
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
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif type_value == "S":
            # Submission workflow: Convert draft or create new
            if existing_draft:
                # Convert existing draft to submission
                serializer = self.get_serializer(
                    existing_draft, data=request.data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save(type="S")
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # Create new submission
                submission_count = ProductiveTestHistory.objects.filter(
                    student=student, productive_test_id=productive_test_id, type="S"
                ).count()
                attempt = submission_count + 1

                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(student=student, attempt=attempt, type="S")
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            {"type": "Invalid type. Must be 'D' or 'S'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
        ],
        responses={
            200: OpenApiResponse(
                description="Danh sách lịch sử thành công",
                response=ProductiveTestHistorySerializer(many=True),
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
            "**Lưu ý:**\n"
            "- `student` và `attempt` tự động được set\n"
            "- `type` mặc định là 'D' (Draft) nếu không gửi\n"
            "- `end_time` bắt buộc khi type='S' (Submission)\n"
            "- `total_time` tự động tính từ start_time và end_time"
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
                    "total_time": 0,
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
                    "total_time": 0,
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
