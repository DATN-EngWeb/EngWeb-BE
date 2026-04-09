from ..authentication import CustomTokenAuthentication
from ..models import Student
from ..permissions import IsOwner
from ..serializers import UserSerializer, StudentSerializer
from ..utils import get_absolute_media_url

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer
)

from rest_framework import serializers
from rest_framework import generics, status
from rest_framework.response import Response
from django.core.files.storage import default_storage

class StudentRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsOwner]
    queryset = Student.objects.select_related("user").all()
    serializer_class = StudentSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"
    http_method_names = ["get", "patch"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @extend_schema(
        summary="Student - View personal profile",
        description=(
            "Get student personal profile by `pk` (pk = user_id/student_id).\n\n"
            "**Conditions:**\n"
            "- Must be logged in\n"
            "- User must be in status `V` (Verified)\n"
            "- Only owner can view their own profile\n\n"
            "**Response:** Data from User + Student. Student fields are only for display, not updated directly from this API."
        ),
        tags=["student"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Student id (same as user_id)",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Student profile data",
                response=inline_serializer(
                    name="StudentProfileResponse",
                    fields={
                        # User fields
                        "id": serializers.IntegerField(),
                        "username": serializers.CharField(),
                        "email": serializers.EmailField(),
                        "file_storage_uuid": serializers.UUIDField(),
                        "full_name": serializers.CharField(allow_null=True),
                        "date_of_birth": serializers.DateField(allow_null=True),
                        "avatar_url": serializers.URLField(allow_null=True),
                        "cover_url": serializers.URLField(allow_null=True),
                        "status": serializers.CharField(),
                        "role": serializers.CharField(),
                        "date_joined": serializers.DateTimeField(),
                        "last_login": serializers.DateTimeField(allow_null=True),
                        "updated_at": serializers.DateTimeField(),
                        # Student fields
                        "cumulative_point": serializers.IntegerField(),
                        "weekly_point": serializers.IntegerField(),
                        "weekly_ai_turn": serializers.IntegerField(),
                        "bonus_ai_turn": serializers.IntegerField(),
                        "completed_test": serializers.IntegerField(),
                        "qualified_test": serializers.IntegerField(),
                        "last_submitted_date": serializers.DateTimeField(allow_null=True),
                        "streak_count": serializers.IntegerField(),
                        "max_streak": serializers.IntegerField(),
                        "level": inline_serializer(
                            name="StudentLevelNestedResponse",
                            fields={
                                "id": serializers.IntegerField(),
                                "level_number": serializers.IntegerField(),
                                "level_title": serializers.CharField(),
                                "level_icon": serializers.URLField(allow_null=True),
                                "min_xp": serializers.IntegerField(),
                                "max_xp": serializers.IntegerField(),
                            },
                        ),
                        "created_at": serializers.DateTimeField(),
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        student = self.get_object()
        user = student.user
        user_data = UserSerializer(user).data
        student_data = StudentSerializer(student).data
        user_data["avatar_url"] = get_absolute_media_url(user_data.get("avatar"))
        user_data["cover_url"] = get_absolute_media_url(user_data.get("cover"))

        user_data.pop("avatar", None)
        user_data.pop("cover", None)

        return Response({**user_data, **student_data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Student - Update personal profile",
        description=(
            "Update student personal profile by `pk` (pk = user_id/student_id).\n\n"
            "**Conditions:**\n"
            "- Must be logged in\n"
            "- User must be in status `V` (Verified)\n"
            "- Only owner can update their own profile\n\n"
            "**FormData (multipart/form-data):**\n"
            "- `user.username`\n"
            "- `user.email`\n"
            "- `user.full_name`\n"
            "- `user.date_of_birth`\n"
            "- `user.avatar` (file)\n"
            "- `user.cover` (file)\n\n"
            "Note: Student fields are not updated directly from this API (only updated by business logic in other places)."
        ),
        tags=["student"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Student id (same as user_id)",
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
            200: OpenApiResponse(
                description="Student profile updated successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "last_login": {"type": "string", "format": "date-time", "nullable": True},
                                "username": {"type": "string"},
                                "is_active": {"type": "boolean"},
                                "date_joined": {"type": "string", "format": "date-time"},
                                "email": {"type": "string"},
                                "file_storage_uuid": {"type": "string", "format": "uuid"},
                                "full_name": {"type": "string", "nullable": True},
                                "date_of_birth": {"type": "string", "format": "date", "nullable": True},
                                "status": {"type": "string"},
                                "role": {"type": "string"},
                                "updated_at": {"type": "string", "format": "date-time"},
                                "avatar_url": {"type": "string", "format": "uri", "nullable": True},
                                "cover_url": {"type": "string", "format": "uri", "nullable": True},
                                "user": {"type": "integer"},
                                "cumulative_point": {"type": "integer"},
                                "weekly_point": {"type": "integer"},
                                "weekly_ai_turn": {"type": "integer"},
                                "bonus_ai_turn": {"type": "integer"},
                                "completed_test": {"type": "integer"},
                                "qualified_test": {"type": "integer"},
                                "last_submitted_date": {"type": "string", "format": "date-time", "nullable": True},
                                "streak_count": {"type": "integer"},
                                "max_streak": {"type": "integer"},
                                "level": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "level_number": {"type": "integer"},
                                        "level_title": {"type": "string"},
                                        "level_icon": {"type": "string", "format": "uri", "nullable": True},
                                        "min_xp": {"type": "integer"},
                                        "max_xp": {"type": "integer"},
                                    },
                                },
                                "created_at": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                },
                examples=[
                    OpenApiExample(
                        name="Student profile update response",
                        value={
                            "message": "Student profile updated successfully",
                            "data": {
                                "id": 2,
                                "last_login": "2026-01-25T16:28:09.508824+07:00",
                                "username": "student_test_api",
                                "is_active": True,
                                "date_joined": "2026-01-25T15:56:33.161493+07:00",
                                "email": "test@gmail.com",
                                "file_storage_uuid": "3f03e010-8443-495e-9b8d-e2181c431947",
                                "full_name": "hehe",
                                "date_of_birth": "2004-09-02",
                                "status": "V",
                                "role": "S",
                                "updated_at": "2026-01-25T15:56:33.601650+07:00",
                                "avatar_url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/avatars/student.png",
                                "cover_url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/covers/test_student_cover.png",
                                "user": 2,
                                "cumulative_point": 0,
                                "weekly_point": 0,
                                "weekly_ai_turn": 4,
                                "bonus_ai_turn": 0,
                                "completed_test": 0,
                                "qualified_test": 0,
                                "last_submitted_date": None,
                                "streak_count": 0,
                                "max_streak": 0,
                                "level": {
                                    "id": 1,
                                    "level_number": 1,
                                    "level_title": "Newbie",
                                    "level_icon": None,
                                    "min_xp": 0,
                                    "max_xp": 299,
                                },
                                "created_at": "2026-01-25T15:56:33.601632+07:00",
                            },
                        },
                    ),
                ],
            ),
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
            # Delete old avatar if it's not the default one
            old_avatar = user.avatar
            if old_avatar and str(old_avatar) != "users/avatars/default-avatar.jpg":
                try:
                    default_storage.delete(str(old_avatar))
                except Exception:
                    pass  # Ignore errors when deleting old file
            user_update_fields["avatar"] = avatar_file

        cover_file = request.FILES.get("user.cover")
        
        if cover_file is not None:
            # Delete old cover if it's not the default one
            old_cover = user.cover
            if old_cover and str(old_cover) != "users/covers/default-cover.jpg":
                try:
                    default_storage.delete(str(old_cover))
                except Exception:
                    pass  # Ignore errors when deleting old file
            user_update_fields["cover"] = cover_file

        user_serializer = UserSerializer(user, data=user_update_fields, partial=True)
        
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()
        
        user_data = UserSerializer(user).data
        user_data["avatar_url"] = get_absolute_media_url(user_data.get("avatar"))
        user_data["cover_url"] = get_absolute_media_url(user_data.get("cover"))
        
        user_data.pop("avatar", None)
        user_data.pop("cover", None)

        student_data = StudentSerializer(student).data

        return Response(
            {"message": "Student profile updated successfully", "data": {**user_data, **student_data}},
            status=status.HTTP_200_OK
        )
