from rest_framework import generics, status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, inline_serializer
from rest_framework import serializers

from ..authentication import CustomTokenAuthentication
from ..models import Student
from ..permissions import IsOwner
from ..serializers import UserSerializer
from ..utils import get_absolute_media_url


class StudentRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsOwner]

    queryset = Student.objects.select_related("user").all()
    serializer_class = UserSerializer

    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    http_method_names = ["get", "patch"]

    @extend_schema(
        summary="Học viên - Xem hồ sơ cá nhân",
        description=(
            "Lấy thông tin hồ sơ học viên theo `pk` (pk = user_id/student_id).\n\n"
            "**Điều kiện:**\n"
            "- Người gọi phải đăng nhập\n"
            "- Tài khoản phải ở trạng thái `V` (Verified)\n"
            "- Chỉ được xem hồ sơ của chính mình (owner)\n\n"
            "**Response:** Dữ liệu từ User + Student. Các field Student chỉ để hiển thị, không update trực tiếp từ API này."
        ),
        tags=["students"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Student id (chính là user_id)",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Student profile"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request, *args, **kwargs):
        student = self.get_object()
        user = student.user

        user_data = UserSerializer(user).data
        student_data = {
            "cumulative_point": student.cumulative_point,
            "weekly_point": student.weekly_point,
            "weekly_ai_turn": student.weekly_ai_turn,
            "bonus_ai_turn": student.bonus_ai_turn,
            "completed_test": student.completed_test,
            "qualified_test": student.qualified_test,
            "last_attempt_at": student.last_attempt_at,
            "streak_count": student.streak_count,
            "max_streak": student.max_streak,
            "level": student.level,
            "title": student.title,
            "created_at": student.created_at,
            "updated_at": student.updated_at,
        }

        user_data["avatar_url"] = get_absolute_media_url(user_data.get("avatar"))
        user_data["cover_url"] = get_absolute_media_url(user_data.get("cover"))
        user_data.pop("avatar", None)
        user_data.pop("cover", None)

        return Response({**user_data, **student_data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Học viên - Cập nhật hồ sơ cá nhân",
        description=(
            "Cập nhật thông tin cá nhân học viên theo `pk` (pk = user_id/student_id).\n\n"
            "**Điều kiện:**\n"
            "- Người gọi phải đăng nhập\n"
            "- Tài khoản phải ở trạng thái `V` (Verified)\n"
            "- Chỉ được cập nhật hồ sơ của chính mình (owner)\n\n"
            "**FormData (multipart/form-data):**\n"
            "- `user.username`\n"
            "- `user.email`\n"
            "- `user.full_name`\n"
            "- `user.date_of_birth`\n"
            "- `user.avatar` (file)\n"
            "- `user.cover` (file)\n\n"
            "Lưu ý: Các trường bên Student không update ở API này (chỉ update bằng business logic ở nơi khác)."
        ),
        tags=["students"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Student id (chính là user_id)",
                required=True,
            ),
        ],
        request=inline_serializer(
            name="StudentUpdateProfileRequest",
            fields={
                "user.username": serializers.CharField(required=False),
                "user.email": serializers.EmailField(required=False),
                "user.full_name": serializers.CharField(required=False),
                "user.date_of_birth": serializers.DateField(required=False),
                "user.avatar": serializers.FileField(required=False),
                "user.cover": serializers.FileField(required=False),
            },
        ),
        responses={
            200: OpenApiResponse(description="Student profile updated"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def patch(self, request, *args, **kwargs):
        student = self.get_object()
        user = student.user

        user_update_fields = {}
        user_fields = ["username", "email", "full_name", "date_of_birth"]
        for field in user_fields:
            key = f"user.{field}"
            if key in request.data:
                user_update_fields[field] = request.data.get(key)

        avatar_file = request.FILES.get("user.avatar")
        if avatar_file is not None:
            user_update_fields["avatar"] = avatar_file

        cover_file = request.FILES.get("user.cover")
        if cover_file is not None:
            user_update_fields["cover"] = cover_file

        user_serializer = UserSerializer(user, data=user_update_fields, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        user_data = UserSerializer(user).data
        user_data["avatar_url"] = get_absolute_media_url(user_data.get("avatar"))
        user_data["cover_url"] = get_absolute_media_url(user_data.get("cover"))
        user_data.pop("avatar", None)
        user_data.pop("cover", None)

        student_data = {
            "cumulative_point": student.cumulative_point,
            "weekly_point": student.weekly_point,
            "weekly_ai_turn": student.weekly_ai_turn,
            "bonus_ai_turn": student.bonus_ai_turn,
            "completed_test": student.completed_test,
            "qualified_test": student.qualified_test,
            "last_attempt_at": student.last_attempt_at,
            "streak_count": student.streak_count,
            "max_streak": student.max_streak,
            "level": student.level,
            "title": student.title,
            "created_at": student.created_at,
            "updated_at": student.updated_at,
        }

        return Response(
            {
                "message": "Student profile updated successfully",
                "data": {**user_data, **student_data},
            },
            status=status.HTTP_200_OK,
        )

