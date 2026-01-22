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
from ..utils import get_absolute_media_url

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    inline_serializer,
)


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class UserListAPIView(generics.ListAPIView):
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
        summary="Admin - Quản lý danh sách người dùng",
        description=(
            "Lấy danh sách người dùng với bộ lọc và phân trang.\n\n"
            "**Query Parameters:**\n"
            "- `role`: Lọc theo vai trò - S (Student), T (Teacher), A (Admin)\n"
            "- `status`: Lọc theo trạng thái - P (Pending), I (Incomplete), W (Waiting), V (Verified), D (Disabled)\n"
            "- `search`: Tìm kiếm theo username hoặc email\n"
            "- `page`: Số trang (mặc định: 1)\n"
            "- `page_size`: Số phần tử mỗi trang (mặc định: 10, tối đa: 100)\n\n"
        ),
        tags=["admin"],
        parameters=[
            OpenApiParameter(
                name="role",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo vai trò - S (Student), T (Teacher), A (Admin)",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo trạng thái - P (Pending), I (Incomplete), W (Waiting), V (Verified), D (Disabled)",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Tìm kiếm theo username hoặc email",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Số trang (mặc định: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Số phần tử mỗi trang (mặc định: 10, tối đa: 100)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Danh sách người dùng có phân trang",
                response={
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "example": 3},
                        "next": {
                            "type": "string",
                            "nullable": True,
                            "example": "http://localhost:8000/api/accounts/users?page=2&page_size=1&role=T&search=teacher&status=W",
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
                                    "id": {"type": "integer", "example": 1023},
                                    "last_login": {
                                        "type": "string",
                                        "format": "date-time",
                                        "example": "2024-01-25T10:30:00+07:00",
                                        "nullable": True,
                                    },
                                    "username": {
                                        "type": "string",
                                        "example": "teacher9",
                                    },
                                    "is_active": {"type": "boolean", "example": True},
                                    "date_joined": {
                                        "type": "string",
                                        "format": "date-time",
                                        "example": "2024-01-24T17:00:00+07:00",
                                    },
                                    "email": {
                                        "type": "string",
                                        "example": "john@example.com",
                                    },
                                    "file_storage_uuid": {
                                        "type": "string",
                                        "example": "550e8400-e29b-41d4-a716-446655440024",
                                    },
                                    "full_name": {
                                        "type": "string",
                                        "example": "Teacher Nine",
                                        "nullable": True,
                                    },
                                    "date_of_birth": {
                                        "type": "string",
                                        "format": "date",
                                        "example": "1990-05-15",
                                        "nullable": True,
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["P", "I", "W", "V", "D"],
                                        "example": "W",
                                    },
                                    "role": {
                                        "type": "string",
                                        "enum": ["S", "T", "A"],
                                        "example": "T",
                                    },
                                    "updated_at": {
                                        "type": "string",
                                        "format": "date-time",
                                        "example": "2024-01-24T17:00:00+07:00",
                                    },
                                    "role_display": {
                                        "type": "string",
                                        "example": "Teacher",
                                    },
                                    "status_display": {
                                        "type": "string",
                                        "example": "Waiting Approval",
                                    },
                                    "avatar_url": {
                                        "type": "string",
                                        "example": "http://localhost:8000/media/avatars/default-avatar.jpg",
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
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.order_by("-date_joined")
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self._add_admin_list_fields(serializer.data)

            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        data = self._add_admin_list_fields(serializer.data)

        return Response(data, status=status.HTTP_200_OK)

    def _add_admin_list_fields(self, data_list):
        request = self.request

        for item in data_list:
            role = item.get("role", "")
            role_display_map = {"S": "Student", "T": "Teacher", "A": "Admin"}
            item["role_display"] = role_display_map.get(role, "")

            status = item.get("status", "")
            status_display_map = {
                "P": "Pending Verification",
                "I": "Incomplete Profile",
                "W": "Waiting Approval",
                "V": "Verified",
                "D": "Disabled",
            }
            item["status_display"] = status_display_map.get(status, "")

            avatar = item.get("avatar")
            item["avatar_url"] = get_absolute_media_url(avatar)
            item.pop("avatar", None)

        return data_list

class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
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
        summary="Admin - Xem chi tiết người dùng",
        description=(
            "Lấy thông tin chi tiết của một user với các luật đặc biệt theo role.\n\n"
            "**Quy tắc:**\n"
            "- **Admin (A)**: Chỉ được xem thông tin của chính mình\n"
            "- **Student (S)**: Không được phép xem thông tin cá nhân của học viên\n"
            "- **Teacher (T)**: Có thể xem thông tin giáo viên bình thường\n\n"
            "**Lưu ý:** Chỉ Admin mới được gọi endpoint này."
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
                description="Thông tin chi tiết của user",
                response=UserSerializer,
            ),
            400: OpenApiResponse(
                description="Không thể xem thông tin của user này",
            ),
            403: OpenApiResponse(
                description="Không có quyền xem thông tin của admin khác",
            ),
            404: OpenApiResponse(
                description="Không tìm thấy user",
            ),
        },
    )
    def get(self, request, pk=None):
        """
        Retrieve user detail with special rules:
        - Admin: Can only view their own profile
        - Student: Cannot view student information
        - Teacher: Can view freely
        """
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check role-based access rules
        if user.role == "A":
            # Admin can only view their own profile
            if user.id != request.user.id:
                return Response(
                    {"error": "You cannot view another admin's profile"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif user.role == "S":
            # Cannot view student information
            return Response(
                {"error": "Cannot view student personal information"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Teacher (T) can be viewed freely

        # Get user data
        user_serializer = UserSerializer(user, context={"request": request})
        user_data = user_serializer.data

        # If teacher, add teacher data
        if user.role == "T":
            try:
                teacher = user.teacher
                teacher_serializer = TeacherSerializer(
                    teacher, context={"request": request}
                )
                teacher_data = teacher_serializer.data

                # Process credentials to absolute URLs
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
                # No teacher profile attached to this user, ignore silently
                pass

        # Add display fields
        user_data["role_display"] = user.get_role_display()
        user_data["status_display"] = user.get_status_display()

        # Convert avatar to avatar_url
        avatar = user_data.get("avatar")
        user_data["avatar_url"] = get_absolute_media_url(avatar)
        user_data.pop("avatar", None)

        return Response(user_data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="user_update",
        summary="Admin - Cập nhật user",
        description=(
            "Cập nhật tài khoản người dùng với **3 trường hợp** dành cho Admin:\n\n"
            "**Case 1: Admin cập nhật thông tin của chính mình (role = 'A', status = 'V', pk = request.user.id)**\n"
            "- Cho phép cập nhật các field cơ bản của User.\n"
            "- Ví dụ request:\n"
            "```json\n"
            "PATCH /api/accounts/users/1/\n"
            "{\n"
            '  "username": "admin_new",\n'
            '  "email": "admin@example.com",\n'
            '  "full_name": "System Admin",\n'
            '  "date_of_birth": "1990-01-01"\n'
            "}\n"
            "```\n\n"
            "**Case 2: Admin enable tài khoản của Student/Teacher khác (role != 'A', status = 'D')**\n"
            "- Không cần request body, chỉ cần gửi PATCH lên đúng `pk` của user.\n"
            "- Ví dụ request:\n"
            "```http\n"
            "PATCH /api/accounts/users/1023/\n"
            "```\n"
            "→ Backend sẽ chuyển `status` từ `D` → `V`.\n\n"
            "**Case 3: Admin accept/reject teacher profile (role = 'T', status = 'W')**\n"
            "- Chỉ cần field `approve` trong body, `user_id` được lấy từ path param `pk`.\n"
            "- Accept thì status sẽ chuyển từ `W` → `V`\n"
            "- Reject thì user sẽ bị xóa\n"
            "- Ví dụ accept:\n"
            "```json\n"
            "PATCH /api/accounts/users/1023/\n"
            "{\n"
            '  "approve": true\n'
            "}\n"
            "```\n"
            "- Ví dụ reject:\n"
            "```json\n"
            "PATCH /api/accounts/users/1023/\n"
            "{\n"
            '  "approve": false\n'
            "}\n"
            "```"
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
        request=inline_serializer(
            name="UserUpdateRequest",
            fields={
                "username": serializers.CharField(required=False),
                "email": serializers.EmailField(required=False),
                "full_name": serializers.CharField(required=False),
                "date_of_birth": serializers.DateField(required=False),
                "avatar": serializers.ImageField(required=False),
                "approve": serializers.BooleanField(
                    required=False,
                    help_text="Required for teacher approval/rejection. true = approve, false = reject",
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Cập nhật user thành công",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Account enabled successfully",
                        },
                        "user_id": {"type": "integer", "example": 12},
                        "status": {"type": "string", "example": "V"},
                    },
                },
            ),
            204: OpenApiResponse(
                description="Từ chối hồ sơ giáo viên và đã xóa user",
            ),
            400: OpenApiResponse(
                description="Request không hợp lệ hoặc user không thể được cập nhật",
            ),
        },
    )
    def patch(self, request, pk=None):
        """
        PATCH method - Three possible actions:
        1. Admin update own profile: role = 'A' and updating self → Update user fields
        2. Enable account: role != 'A' and status = 'D' → 'V'
        3. Accept/Reject teacher: role = 'T' and status = 'W' → 'V' or delete
        """
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Case 1: Admin updating own profile (role = 'A', status = 'V', updating self)
        if user.role == "A" and user.id == request.user.id and user.status == "V":
            # Update user fields using serializer
            serializer = UserSerializer(
                user, data=request.data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                # Return updated user data
                updated_data = serializer.data
                updated_data["role_display"] = user.get_role_display()
                updated_data["status_display"] = user.get_status_display()
                # Convert avatar to avatar_url
                avatar = updated_data.get("avatar")
                updated_data["avatar_url"] = get_absolute_media_url(avatar)
                updated_data.pop("avatar", None)
                return Response(
                    {
                        "message": "Profile updated successfully",
                        "user": updated_data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Case 2: Enable account (role != 'A' and status = 'D')
        elif user.role != "A" and user.status == "D":
            user.status = "V"
            user.save()
            return Response(
                {
                    "message": "Account enabled successfully",
                    "user_id": user.id,
                    "status": user.status,
                },
                status=status.HTTP_200_OK,
            )

        # Case 3: Accept/Reject teacher profile (role = 'T' and status = 'W')
        elif user.role == "T" and user.status == "W":
            approve = request.data.get("approve")

            if approve is None:
                return Response(
                    {
                        "error": "approve field is required for teacher approval/rejection"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if approve:
                # Accept: Change status to 'V'
                user.status = "V"
                user.save()
                return Response(
                    {
                        "message": "Teacher profile approved successfully",
                        "user_id": user.id,
                        "status": user.status,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                # Reject: Delete user (Teacher will be deleted via CASCADE)
                user.delete()
                return Response(
                    {"message": "Teacher profile rejected and user deleted"},
                    status=status.HTTP_204_NO_CONTENT,
                )

        # If none of the conditions match (invalid combination of role/status or wrong format)
        else:
            return Response(
                {
                    "error": "User cannot be updated with current status and role "
                    "or request body format is invalid for this user type."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        operation_id="user_destroy",
        summary="Admin - Vô hiệu hóa user (soft delete)",
        description=(
            "Vô hiệu hóa tài khoản người dùng (soft delete).\n\n"
            "**Điều kiện:**\n"
            "- User có `role != 'A'`\n"
            "- User có `status = 'V'`\n\n"
            "**Kết quả:**\n"
            "- Trạng thái user sẽ chuyển từ `V` sang `D`\n\n"
            "**Lưu ý:** Chỉ Admin mới được gọi endpoint này."
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
                description="Vô hiệu hóa user thành công",
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
                description="User không thể bị vô hiệu hóa (phải có role != 'A' và status = 'V')",
            ),
        },
    )
    def delete(self, request, pk=None):
        """
        DELETE method - Disable user account
        Conditions: role != 'A' and status = 'V' → Change to 'D'
        """
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check conditions: role != 'A' and status = 'V'
        if user.role != "A" and user.status == "V":
            user.status = "D"
            user.save()
            return Response(
                {
                    "message": "User disabled successfully",
                    "user_id": user.id,
                    "status": user.status,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "error": "User cannot be disabled. User must have role != 'A' and status = 'V'"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
