import django_filters
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status, serializers
from django.utils import timezone
from datetime import timedelta

from accounts.permissions import IsOwner

from .filters import UserLevelFilter
from .models import UserLevel
from .serializers import UserLevelSerializer


class UserLevelListAPIView(generics.ListAPIView):
    queryset = UserLevel.objects.all().order_by("min_xp")
    serializer_class = UserLevelSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = UserLevelFilter

    @extend_schema(
        summary="Danh sách level của người dùng",
        description=(
            "Lấy danh sách level của người dùng, sắp xếp theo `min_xp` tăng dần. "
            "Hỗ trợ lọc theo `level_number` và `level_title`."
        ),
        tags=["user-progress"],
        parameters=[
            OpenApiParameter(
                name="level_number",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Lọc theo số level chính xác",
            ),
            OpenApiParameter(
                name="level_title",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Lọc theo tên level (không phân biệt hoa thường, tìm gần đúng)",
            ),
        ],
        responses={
            200: UserLevelSerializer(many=True),
            401: OpenApiResponse(description="Cần đăng nhập"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserLevelRetrieveAPIView(generics.RetrieveAPIView):
    queryset = UserLevel.objects.all()
    serializer_class = UserLevelSerializer
    lookup_field = "level_number"
    lookup_url_kwarg = "level_number"

    @extend_schema(
        summary="Lấy chi tiết một level",
        description="Lấy thông tin chi tiết của một level cụ thể theo số level.",
        tags=["user-progress"],
        parameters=[
            OpenApiParameter(
                name="level_number",
                type=int,
                location=OpenApiParameter.PATH,
                required=True,
                description="Số level cần lấy",
            ),
        ],
        responses={
            200: UserLevelSerializer,
            401: OpenApiResponse(description="Cần đăng nhập"),
            404: OpenApiResponse(description="Không tìm thấy level"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CurrentUserStreakAPIView(generics.GenericAPIView):
    permission_classes = [IsOwner]

    @extend_schema(
        summary="Lấy streak hiện tại của user",
        description=(
            "Lấy thông tin streak của user hiện tại gồm `last_submitted_date`, "
            "`streak_count`, `max_streak`, `is_streak_lit_today`.\n\n"
            "**Logic kiểm tra mất chuỗi khi truy vấn:**\n"
            "- Nếu `last_submitted_date` cũ hơn hôm qua, hệ thống tự cập nhật `streak_count` về `0`\n"
            "- Nếu `last_submitted_date` là hôm qua hoặc hôm nay thì giữ nguyên streak\n"
            "- `is_streak_lit_today=true` khi user đã submit trong ngày hôm nay\n"
            "- `max_streak` không thay đổi"
        ),
        tags=["user-progress"],
        responses={
            200: OpenApiResponse(
                description="Lấy thông tin streak thành công",
                response=inline_serializer(
                    name="CurrentUserStreakResponse",
                    fields={
                        "last_submitted_date": serializers.DateTimeField(allow_null=True),
                        "streak_count": serializers.IntegerField(),
                        "max_streak": serializers.IntegerField(),
                        "is_streak_lit_today": serializers.BooleanField(),
                    },
                ),
            ),
            401: OpenApiResponse(description="Cần đăng nhập"),
            403: OpenApiResponse(description="Chỉ học viên mới có thể truy cập"),
        },
    )
    def get(self, request, *args, **kwargs):
        user = request.user

        if user.role != "S" or not hasattr(user, "student"):
            raise PermissionDenied("Only Student can access this resource.")

        student = user.student
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        if student.streak_count > 0:
            if not student.last_submitted_date:
                student.streak_count = 0
                student.save(update_fields=["streak_count"])
            else:
                last_submitted_date = timezone.localdate(student.last_submitted_date)
                if last_submitted_date < yesterday:
                    student.streak_count = 0
                    student.save(update_fields=["streak_count"])

        is_streak_lit_today = False
        if student.last_submitted_date:
            is_streak_lit_today = timezone.localdate(student.last_submitted_date) == today

        return Response(
            {
                "last_submitted_date": student.last_submitted_date,
                "streak_count": student.streak_count,
                "max_streak": student.max_streak,
                "is_streak_lit_today": is_streak_lit_today,
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserAITurnView(generics.GenericAPIView):
    permission_classes = [IsOwner]

    @extend_schema(
        summary="Lấy số lượt AI còn lại của user hiện tại",
        description=(
            "Lấy nhanh số lượt AI còn lại của user hiện tại\n\n"
            "Role:\n"
            "- `S`: Student\n"
            "- `T`: Teacher\n\n"
            "Student: trả về `weekly_ai_turn`, `bonus_ai_turn`, `total_ai_turn`\n\n"
            "Teacher: trả về `weekly_ai_turn`, `bonus_ai_turn=0`, `total_ai_turn`"
        ),
        tags=["user-progress"],
        examples=[
            OpenApiExample(
                "Student response",
                value={
                    "role": "S",
                    "weekly_ai_turn": 3,
                    "bonus_ai_turn": 1,
                    "total_ai_turn": 4,
                },
                response_only=True,
            ),
            OpenApiExample(
                "Teacher response",
                value={
                    "role": "T",
                    "weekly_ai_turn": 2,
                    "bonus_ai_turn": 0,
                    "total_ai_turn": 2,
                },
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Lấy thông tin lượt AI thành công",
                response=inline_serializer(
                    name="CurrentUserAITurnResponse",
                    fields={
                        "role": serializers.ChoiceField(
                            choices=[("S", "Student"), ("T", "Teacher")],
                            help_text="User role code: S = Student, T = Teacher",
                        ),
                        "weekly_ai_turn": serializers.IntegerField(),
                        "bonus_ai_turn": serializers.IntegerField(),
                        "total_ai_turn": serializers.IntegerField(),
                    },
                ),
            ),
            401: OpenApiResponse(description="Cần đăng nhập"),
            403: OpenApiResponse(
                description="Chỉ học viên hoặc giáo viên mới có thể truy cập"
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        user = request.user

        if user.role == "S" and hasattr(user, "student"):
            weekly_ai_turn = user.student.weekly_ai_turn
            bonus_ai_turn = user.student.bonus_ai_turn
        elif user.role == "T" and hasattr(user, "teacher"):
            weekly_ai_turn = user.teacher.weekly_ai_turn
            bonus_ai_turn = 0
        else:
            raise PermissionDenied("Only Student or Teacher can access this resource.")

        return Response(
            {
                "role": user.role,
                "weekly_ai_turn": weekly_ai_turn,
                "bonus_ai_turn": bonus_ai_turn,
                "total_ai_turn": weekly_ai_turn + bonus_ai_turn,
            },
            status=status.HTTP_200_OK,
        )
