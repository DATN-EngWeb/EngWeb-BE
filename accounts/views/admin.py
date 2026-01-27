from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers
import django_filters

from ..models import User, Teacher
from ..serializers import UserSerializer, TeacherSerializer
from ..filters import UserFilter
from ..permissions import IsAdmin
from ..authentication import CustomTokenAuthentication
from ..utils import get_absolute_media_url, delete_user_storage_folder

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample,
    inline_serializer,
)

class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class AdminListUserAPIView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    authentication_classes = [CustomTokenAuthentication]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = UserFilter
    pagination_class = UserPagination

    def get_queryset(self):
        return User.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @extend_schema(
        operation_id="user_list_get",
        summary="Admin - User List API",
        description=(
            "Get user list with filters and pagination.\n\n"
            "**Query Parameters:**\n"
            "- `role`: Filter by role - S (Student), T (Teacher), A (Admin)\n"
            "- `status`: Filter by status - P (Pending), I (Incomplete), W (Waiting), V (Verified), D (Disabled)\n"
            "- `search`: Search by username or email\n"
            "- `page`: Page number (default: 1)\n"
            "- `page_size`: Number of items per page (default: 10, max: 100)\n\n"
        ),
        tags=["admin"],
        parameters=[
            OpenApiParameter(
                name="role",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by role - S (Student), T (Teacher), A (Admin)",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status - P (Pending), I (Incomplete), W (Waiting), V (Verified), D (Disabled)",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by username or email",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number (default: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 10, max: 100)",
                required=False,
            ),
        ],
        examples=[
            OpenApiExample(
                name="Example Response",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 2,
                            "last_login": None,
                            "username": "vunewbie",
                            "is_active": True,
                            "date_joined": "2026-01-24T14:36:16.713777+07:00",
                            "email": "vulocninh1@gmail.com",
                            "file_storage_uuid": "8166784b-2c0a-4430-982a-0d13125b8cdb",
                            "full_name": "Nguyễn Hoàng Vũ",
                            "date_of_birth": "2004-09-03",
                            "cover": "/media/users/covers/default-cover.jpg",
                            "status": "W",
                            "role": "T",
                            "updated_at": "2026-01-24T14:38:49.292474+07:00",
                            "role_display": "Teacher",
                            "status_display": "Waiting Approval",
                            "avatar_url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/avatars/Gemini_Generated_Image_3cek3u3cek3u3cek.png",
                        }
                    ],
                },
                response_only=True,
                status_codes=["200"],
            )
        ],
        responses={
            200: OpenApiResponse(
                description="User list with pagination",
                response={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                        "results": {"type": "array", "items": {}},
                    },
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.order_by("-date_joined")
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        role_display_map = {"S": "Student", "T": "Teacher", "A": "Admin"}
        status_display_map = {
            "P": "Pending Verification",
            "I": "Incomplete Profile",
            "W": "Waiting Approval",
            "V": "Verified",
            "D": "Disabled",
        }

        for item in data:
            item["role_display"] = role_display_map.get(item.get("role", ""), "")
            item["status_display"] = status_display_map.get(item.get("status", ""), "")
            item["avatar_url"] = get_absolute_media_url(item.get("avatar"))
            item.pop("avatar", None)

        if page is not None:
            return self.get_paginated_response(data)

        return Response(data, status=status.HTTP_200_OK)

class AdminRetrieveUpdateDestroyUserAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    authentication_classes = [CustomTokenAuthentication]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"
    http_method_names = ["get", "patch", "delete"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @extend_schema(
        operation_id="user_retrieve",
        summary="Admin - User Detail API",
        description=(
            "Get user detail with special rules based on role.\n\n"
            "**Rules:**\n"
            "- **Admin (A)**: Only view own profile\n"
            "- **Student (S)**: Cannot view student personal information\n"
            "- **Teacher (T)**: Can view teacher information\n\n"
            "**Note:** Only admin can call this endpoint."
        ),
        tags=["admin"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
        ],
        examples=[
            OpenApiExample(
                name="Example Response for Teacher",
                value={
                    "id": 2,
                    "last_login": None,
                    "username": "vunewbie",
                    "is_active": True,
                    "date_joined": "2026-01-24T14:36:16.713777+07:00",
                    "email": "vulocninh1@gmail.com",
                    "file_storage_uuid": "8166784b-2c0a-4430-982a-0d13125b8cdb",
                    "full_name": "Nguyễn Hoàng Vũ",
                    "date_of_birth": "2004-09-03",
                    "cover": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/covers/default-cover.jpg",
                    "status": "W",
                    "role": "T",
                    "updated_at": "2026-01-24T14:38:49.292474+07:00",
                    "current_workplace": "Pizza 4P's",
                    "teacher_type": "C",
                    "experience_year": 1,
                    "introduction": "I am a Data Engineer.",
                    "credentials": [
                        {
                            "id": 0,
                            "url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/teachers/credentials/8166784b-2c0a-4430-982a-0d13125b8cdb/credential_0.jpg",
                            "name": "credential_0.jpg",
                            "size": 2791601,
                            "type": "image/jpeg"
                        },
                        {
                            "id": 1,
                            "url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/teachers/credentials/8166784b-2c0a-4430-982a-0d13125b8cdb/credential_1.jpg",
                            "name": "credential_1.jpg",
                            "size": 4357,
                            "type": "image/jpeg"
                        }
                    ],
                    "teacher_type_display": "Center Teacher",
                    "role_display": "Teacher",
                    "status_display": "Waiting Approval",
                    "avatar_url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/avatars/Gemini_Generated_Image_3cek3u3cek3u3cek.png",
                },
                response_only=True,
                status_codes=["200"],
            )
        ],
        responses={
            200: OpenApiResponse(
                description="User detail",
                response=UserSerializer,
            )
        },
    )
    def get(self, request, pk=None):
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.role == "A":
            if user.id != request.user.id:
                return Response(
                    {"detail": "You cannot view another admin's profile"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        elif user.role == "S":
            return Response(
                {"detail": "Cannot view student personal information"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user_serializer = UserSerializer(user, context={"request": request})
        user_data = user_serializer.data

        if user.role == "T":
            try:
                teacher = user.teacher
                teacher_serializer = TeacherSerializer(teacher, context={"request": request})
                teacher_data = teacher_serializer.data
                credentials = teacher_data.get("credentials", [])

                if isinstance(credentials, list):
                    processed_credentials = []

                    for cred in credentials:
                        cred_url = cred.get("url", "") if isinstance(cred, dict) else ""
                        
                        if cred_url:
                            processed_cred = cred.copy()
                            processed_cred["url"] = get_absolute_media_url(cred_url)
                            
                            processed_credentials.append(processed_cred)
                        else:
                            processed_credentials.append(cred)
                    
                    teacher_data["credentials"] = processed_credentials

                user_data.update(teacher_data)
                user_data["teacher_type_display"] = teacher.get_teacher_type_display()
            
            except Teacher.DoesNotExist:
                return Response(
                    {"detail": "Data integrity error: User with role 'T' has no Teacher profile."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        user_data["role_display"] = user.get_role_display()
        user_data["status_display"] = user.get_status_display()

        avatar = user_data.get("avatar")
        user_data["avatar_url"] = get_absolute_media_url(avatar)
        user_data.pop("avatar", None)

        return Response(user_data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="user_update",
        summary="Admin - Update User API",
        description=(
            "Update user account with an `action` flag to specify the operation.\n\n"
            "**Actions:**\n"
            "- `update_profile`: Admin updates their own profile.\n"
            "- `enable_account`: Admin re-enables a disabled Student or Teacher account.\n"
            "- `review_profile`: Admin approves or rejects a teacher's profile submission.\n\n"
            "**Note:** `password` field is ignored in `update_profile` action."
        ),
        tags=["admin"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="User ID",
                required=True,
            ),
        ],
        request=inline_serializer(
            name="UserUpdateRequest",
            fields={
                "action": serializers.ChoiceField(choices=["update_profile", "enable_account", "review_profile"], required=True),
                "username": serializers.CharField(required=False),
                "email": serializers.EmailField(required=False),
                "full_name": serializers.CharField(required=False),
                "date_of_birth": serializers.DateField(required=False),
                "avatar": serializers.ImageField(required=False),
                "cover": serializers.ImageField(required=False),
                "approve": serializers.BooleanField(
                    required=False,
                    help_text="Required for `review_profile` action. `true` to approve, `false` to reject.",
                ),
            },
        ),
        examples=[
            OpenApiExample(
                name="Case 1: Admin Update Own Profile (Request)",
                value={
                    "action": "update_profile",
                    "email": "new.admin.email@example.com",
                    "full_name": "Admin Name",
                    "date_of_birth": "2000-01-01"
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Case 1: Admin Update Own Profile (Response)",
                value={
                    "message": "Profile updated successfully",
                    "user": {
                        "id": 1,
                        "last_login": "2026-01-25T00:22:35.838083+07:00",
                        "username": "admin",
                        "is_active": True,
                        "date_joined": "2026-01-25T00:08:12.799533+07:00",
                        "email": "new.admin.email@example.com",
                        "file_storage_uuid": "0cdbf098-a528-4ae8-ab29-1a8e319e3ab6",
                        "full_name": "Admin Name",
                        "date_of_birth": "2000-01-01",
                        "cover": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/covers/134052332635336370.jpg",
                        "status": "V",
                        "role": "A",
                        "updated_at": "2026-01-25T00:22:47.234716+07:00",
                        "role_display": "Admin",
                        "status_display": "Verified",
                        "avatar_url": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/avatars/image_0.jpg",
                    }
                },
                response_only=True,
                status_codes=["200"]
            ),
            OpenApiExample(
                name="Case 2: Enable Account",
                value={"action": "enable_account"},
                request_only=True,
            ),
            OpenApiExample(
                name="Case 2: Enable Account (Response)",
                value={
                    "message": "Account enabled successfully",
                    "user_id": 2,
                    "status": "V",
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                name="Case 3: Reject Profile",
                value={"action": "review_profile", "approve": False},
                request_only=True,
            ),
            OpenApiExample(
                name="Case 3: Reject Profile (Response)",
                value={"message": "Teacher profile rejected and user deleted"},
                response_only=True,
                status_codes=["204"],
            ),
        ],
        responses={
            200: OpenApiResponse(description="Update user successfully"),
            204: OpenApiResponse(description="Reject teacher profile and delete user"),
            400: OpenApiResponse(description="Invalid request or user cannot be updated"),
        },
    )
    def patch(self, request, pk=None):
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")

        if action == "update_profile":
            if user.role == "A" and user.id == request.user.id and user.status == "V":
                update_data = {}
                for field in ["username", "email", "full_name", "date_of_birth"]:
                    if field in request.data:
                        update_data[field] = request.data[field]
                
                if 'avatar' in request.FILES:
                    update_data['avatar'] = request.FILES['avatar']
                if 'cover' in request.FILES:
                    update_data['cover'] = request.FILES['cover']

                serializer = UserSerializer(user, data=update_data, partial=True, context={"request": request})

                if serializer.is_valid():
                    serializer.save()

                    updated_data = serializer.data
                    updated_data["role_display"] = user.get_role_display()
                    updated_data["status_display"] = user.get_status_display()
                    avatar = updated_data.get("avatar")
                    updated_data["avatar_url"] = get_absolute_media_url(avatar)
                    
                    updated_data.pop("avatar", None)
                    
                    return Response({"message": "Profile updated successfully", "user": updated_data}, status=status.HTTP_200_OK)
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": "Action 'update_profile' is only allowed for the admin to update their own profile."}, status=status.HTTP_403_FORBIDDEN)

        elif action == "enable_account":
            if user.role != "A" and user.status == "D":
                user.status = "V"
                user.save()

                response = {
                    "message": "Account enabled successfully",
                    "user_id": user.id,
                    "status": user.status,
                }
                return Response(response, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Action 'enable_account' is only for disabled Student/Teacher accounts."}, status=status.HTTP_400_BAD_REQUEST)

        elif action == "review_profile":
            if user.role == "T" and user.status == "W":
                approve = request.data.get("approve")
                if approve is None:
                    return Response({"error": "'approve' field is required for 'review_profile' action"}, status=status.HTTP_400_BAD_REQUEST)

                if approve:
                    user.status = "V"
                    user.save()
                    response = {
                        "message": "Teacher profile approved successfully",
                        "user_id": user.id,
                        "status": user.status
                    }
                    return Response(response, status=status.HTTP_200_OK)
                else:
                    # Delete all files in teacher's storage folder before deleting user
                    delete_user_storage_folder(user)
                    user.delete()
                    return Response({"message": "Teacher profile rejected and user deleted"}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"detail": "Action 'review_profile' is only for waiting Teacher profiles."}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"detail": "Invalid or missing 'action' field."}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="user_destroy",
        summary="Admin - Disable User API",
        description=(
            "Disable user account (soft delete).\n\n"
            "**Conditions:**\n"
            "- User has `role != 'A'`\n"
            "- User has `status = 'V'`\n\n"
            "**Result:**\n"
            "- User status will change from `V` to `D`\n\n"
            "**Note:** Only admin can call this endpoint."
        ),
        tags=["admin"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID của user",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Disable user successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "User disabled successfully",
                        },
                        "user_id": {"type": "integer", "example": 12},
                        "status": {"type": "string", "example": "D"},
                    },
                },
            ),
            400: OpenApiResponse(
                description="User cannot be disabled (must have role != 'A' and status = 'V')",
            ),
        },
    )
    def delete(self, request, pk=None):
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.role != "A" and user.status == "V":
            user.status = "D"
            user.save()
            
            response = {
                "message": "User disabled successfully",
                "user_id": user.id,
                "status": user.status,
            }
            return Response(response, status=status.HTTP_200_OK)

        return Response(
            {"detail": "User cannot be disabled. User must have role != 'A' and status = 'V'"},
            status=status.HTTP_400_BAD_REQUEST
        )
