from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import jwt
import requests
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .models import User, Student, Teacher
from .serializers import (
    UserSerializer,
    StudentSerializer,
    TeacherSerializer,
    CustomTokenObtainPairSerializer,
)
from .filters import AdminUserFilter
from .permissions import IsAdmin
from .utils import (
    create_otp_code,
    cache_register_otp,
    send_registration_otp_email,
    resend_registration_otp_email,
    verify_registration_otp,
    delete_registration_otp_cache,
    process_credential_files,
    cache_forgot_password_otp,
    send_forgot_password_otp_email,
    resend_forgot_password_otp_email,
    download_and_save_avatar,
    generate_unique_username,
    get_absolute_media_url,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
import django_filters


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="Đăng nhập tài khoản",
        description=(
            "Xác thực người dùng và cấp JWT tokens.\n\n"
            "**Luồng xử lý dựa trên trạng thái tài khoản:**\n\n"
            "- **P (Pending Verification)**: Gửi OTP xác thực email, yêu cầu verify\n"
            "- **I (Incomplete Profile)**: Teacher chưa hoàn thành hồ sơ, yêu cầu upload certificate\n"
            "- **W (Waiting Approval)**: Chờ admin phê duyệt, không cấp tokens\n"
            "- **V (Verified)**: Cấp access token và refresh token\n"
            "- **D (Disabled)**: Tài khoản bị vô hiệu hóa, không cho phép đăng nhập\n\n"
            "**Tham số đầu vào:**\n"
            "- `username`: username hoặc email\n"
            "- `password`: mật khẩu"
        ),
        tags=["accounts"],
        request=CustomTokenObtainPairSerializer,
        responses={
            200: OpenApiResponse(
                description="Login successful - Student verified or Teacher waiting approval",
                response={
                    "type": "object",
                    "properties": {
                        "access": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "refresh": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["V", "I"],
                            "example": "V",
                        },
                        "username": {"type": "string", "example": "john_doe"},
                        "avatar": {
                            "type": "string",
                            "nullable": True,
                            "example": "https://example.com/avatars/user.jpg",
                        },
                    },
                    "required": ["access", "refresh", "status", "username"],
                },
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Đăng xuất tài khoản",
        description=(
            "Đăng xuất người dùng bằng cách blacklist refresh token.\n\n"
            "**Yêu cầu:**\n"
            "- Phải được xác thực (có refresh token hợp lệ)\n"
            "- Gửi refresh token để blacklist\n\n"
            "**Tham số đầu vào:**\n"
            "- `refresh`: Refresh token cần blacklist (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="LogoutRequest",
            fields={
                "refresh": serializers.CharField(
                    required=True,
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Logout successful",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Logged out successfully",
                        },
                    },
                    "required": ["message"],
                },
            ),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Logged out successfully"}, status=status.HTTP_200_OK
        )


class UserRegistrationAPIView(generics.GenericAPIView):
    """Create User model and send OTP email. Status is set to 'P' (Pending Verification)"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Đăng ký tài khoản",
        description=(
            "Tạo user mới và gửi OTP xác thực email.\n\n"
            "- Role = `S`: Student\n"
            "- Role = `T`: Teacher\n"
            "- User được tạo với trạng thái `P` (Pending Verification)"
        ),
        tags=["accounts"],
        request=UserSerializer,
        responses={
            201: OpenApiResponse(
                description="User registered successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Student account registered successfully. Please check your email to verify your account.",
                        },
                        "user_id": {"type": "integer", "example": 12},
                    },
                    "required": ["message", "user_id"],
                },
            ),
        },
    )
    def post(self, request):
        role = request.data.get("role", "").upper()

        # Validate role
        if role not in ["S", "T"]:
            return Response(
                {"detail": "Invalid role. Must be 'S' (Student) or 'T' (Teacher)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate user data using UserSerializer
        user_serializer = UserSerializer(data=request.data)

        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = user_serializer.save()

        # Generate OTP and cache it
        otp_code = create_otp_code()
        cache_register_otp(user.id, otp_code, user.email)

        # Send OTP email
        send_registration_otp_email(user.email, otp_code)

        # Response message based on role
        role_name = "Student" if role == "S" else "Teacher"
        response = {
            "message": f"{role_name} account registered successfully. Please check your email to verify your account.",
            "user_id": user.id,
        }

        return Response(response, status=status.HTTP_201_CREATED)


class VerifyRegistrationOTPAPIView(generics.GenericAPIView):
    """Verify OTP code for registration. Updates user status:
    + Student: P → V (Verified)
    + Teacher: P → I (Incomplete Profile)
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Xác thực OTP đăng ký tài khoản",
        description=(
            "Xác minh mã OTP và cập nhật trạng thái người dùng sau khi đăng ký.\n\n"
            "**Luồng xử lý theo vai trò:**\n\n"
            "- **Student (S)**: P (Pending) → V (Verified) - Có thể đăng nhập ngay\n"
            "- **Teacher (T)**: P (Pending) → I (Incomplete Profile) - Cần hoàn thành hồ sơ\n\n"
            "**Tham số đầu vào:**\n"
            "- `user_id`: ID của người dùng (bắt buộc)\n"
            "- `otp_code`: Mã OTP gửi đến email (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="VerifyRegistrationOTPRequest",
            fields={
                "user_id": serializers.IntegerField(required=True),
                "otp_code": serializers.CharField(
                    required=True, help_text="Mã OTP gửi đến email"
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="OTP verified successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Student account verified successfully.",
                        },
                        "user_id": {"type": "integer", "example": 12},
                        "status": {
                            "type": "string",
                            "enum": ["V", "I"],
                            "example": "V",
                        },
                    },
                    "required": ["message", "user_id", "status"],
                },
            ),
        },
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        otp_code = request.data.get("otp_code")

        # Verify OTP
        try:
            cache_data = verify_registration_otp(user_id, otp_code)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Get user and verify status is Pending
        try:
            user = User.objects.get(id=user_id, status="P")
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found or already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update status based on role
        if user.role == "S":
            user.status = "V"
        elif user.role == "T":
            user.status = "I"
        else:
            return Response(
                {"detail": "Invalid user role."}, status=status.HTTP_400_BAD_REQUEST
            )

        user.save()

        # Delete OTP from cache
        delete_registration_otp_cache(user_id)

        # Response message based on role
        role_name = "Student" if user.role == "S" else "Teacher"

        # Create Student record if role is Student. Teacher record will be created later when they submit profile
        if user.role == "S":
            student_serializer = StudentSerializer(data={}, context={"user": user})
            student_serializer.is_valid()
            student_serializer.save()

        response = {
            "message": f"{role_name} account verified successfully.",
            "user_id": user.id,
            "status": user.status,
        }

        return Response(response, status=status.HTTP_200_OK)


class ResendRegistrationOTPAPIView(generics.GenericAPIView):
    """Resend OTP code for registration"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Gửi lại mã OTP đăng ký",
        description=(
            "Gửi lại mã OTP xác thực email cho người dùng.\n\n"
            "- Sử dụng khi người dùng không nhận được OTP hoặc OTP hết hạn\n"
            "- Mã OTP mới sẽ được gửi đến email đã đăng ký\n\n"
            "**Tham số đầu vào:**\n"
            "- `user_id`: ID của người dùng (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="ResendRegistrationOTPRequest",
            fields={
                "user_id": serializers.IntegerField(required=True),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="OTP resent successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "OTP code has been resent to your email.",
                        },
                    },
                    "required": ["message"],
                },
            ),
        },
    )
    def post(self, request):
        user_id = request.data.get("user_id")

        # Validate input
        if not user_id:
            return Response(
                {"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Resend OTP
        try:
            resend_registration_otp_email(user_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "OTP code has been resent to your email."},
            status=status.HTTP_200_OK,
        )


class TeacherAPIView(generics.GenericAPIView):
    """
    Complete teacher profile after OTP verification (status I -> W)

    Expected FormData format:
    - user_id: integer (required)
    - user.full_name: string (required)
    - user.date_of_birth: date string YYYY-MM-DD (required)
    - user.avatar: image file (required)
    - current_workplace: string (required)
    - teacher_type: string 'S'|'C'|'F' (required)
    - experience_year: integer (required)
    - introduction: string (required)
    - credentials: file (optional, can send multiple with same key)
    """

    serializer_class = TeacherSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Hoàn thành hồ sơ giáo viên",
        description=(
            "Hoàn thành hồ sơ giáo viên sau khi xác thực email (chuyển từ trạng thái I → W).\n\n"
            "**Yêu cầu:**\n"
            "- User phải ở trạng thái I (Incomplete Profile)\n"
            "- Phải upload ít nhất 1 chứng chỉ (certificate)\n\n"
            "**Luồng xử lý:**\n"
            "- Cập nhật thông tin người dùng (full_name, date_of_birth, avatar)\n"
            "- Lưu thông tin giáo viên (nơi làm việc, loại giáo viên, kinh nghiệm, giới thiệu)\n"
            "- Tải lên chứng chỉ\n"
            "- Chuyển trạng thái từ I → W (Waiting Approval)\n\n"
            "**Tham số đầu vào (FormData):**\n"
            "- `user_id`: ID người dùng (bắt buộc)\n"
            "- `user.full_name`: Họ và tên (bắt buộc)\n"
            "- `user.date_of_birth`: Ngày sinh (YYYY-MM-DD, bắt buộc)\n"
            "- `user.avatar`: Ảnh đại diện (bắt buộc)\n"
            "- `current_workplace`: Nơi làm việc hiện tại (bắt buộc)\n"
            "- `teacher_type`: Loại giáo viên - S (School), C (Center), F (Freelance) (bắt buộc)\n"
            "- `experience_year`: Năm kinh nghiệm (bắt buộc)\n"
            "- `introduction`: Giới thiệu bản thân (bắt buộc)\n"
            "- `credentials`: Chứng chỉ/bằng cấp (có thể upload nhiều file, bắt buộc ít nhất 1)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="TeacherProfileRequest",
            fields={
                "user_id": serializers.IntegerField(required=True),
                "user": inline_serializer(
                    name="UserDataRequest",
                    fields={
                        "full_name": serializers.CharField(required=True),
                        "date_of_birth": serializers.DateField(required=True),
                        "avatar": serializers.FileField(required=True),
                    },
                ),
                "current_workplace": serializers.CharField(required=True),
                "teacher_type": serializers.ChoiceField(
                    choices=["S", "C", "F"], required=True
                ),
                "experience_year": serializers.IntegerField(required=True),
                "introduction": serializers.CharField(required=True),
                "credentials": serializers.ListField(
                    child=serializers.FileField(), required=True
                ),
            },
        ),
        responses={
            201: OpenApiResponse(
                description="Teacher profile submitted successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Teacher profile submitted successfully. Awaiting approval.",
                        },
                        "user_id": {"type": "integer", "example": 12},
                        "status": {"type": "string", "enum": ["W"], "example": "W"},
                        "teacher_id": {"type": "integer", "example": 12},
                    },
                    "required": ["message", "user_id", "status", "teacher_id"],
                },
            ),
        },
    )
    def post(self, request):
        # Get user_id from form data
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "user_id must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get and validate user
        try:
            user = User.objects.get(id=user_id, role="T")
        except User.DoesNotExist:
            return Response(
                {"detail": "Teacher not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Only allow when status is Incomplete profile
        if user.status != "I":
            return Response(
                {"detail": "Profile already completed or not allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate and update User fields directly
        user_errors = {}
        full_name = request.data.get("user.full_name", "").strip()
        date_of_birth = request.data.get("user.date_of_birth")
        avatar_file = request.FILES.get("user.avatar")

        if not full_name:
            user_errors["full_name"] = "This field is required."
        if not date_of_birth:
            user_errors["date_of_birth"] = "This field is required."
        if not avatar_file:
            user_errors["avatar"] = "This field is required."

        if user_errors:
            return Response({"user": user_errors}, status=status.HTTP_400_BAD_REQUEST)

        # Update User fields
        user.full_name = full_name
        user.date_of_birth = date_of_birth
        if avatar_file:
            user.avatar = avatar_file

        # Process credential files
        credentials_data = process_credential_files(request.FILES, user)

        # Validate at least one certificate is required
        if (
            not credentials_data.get("certificates")
            or len(credentials_data.get("certificates", [])) == 0
        ):
            return Response(
                {"credentials": "At least one certificate is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prepare data for serializer (only Teacher fields, no nested user)
        serializer_data = {
            "current_workplace": request.data.get("current_workplace", "").strip(),
            "teacher_type": request.data.get("teacher_type"),
            "experience_year": request.data.get("experience_year"),
            "introduction": request.data.get("introduction", "").strip(),
            "credentials": credentials_data,
        }

        serializer = self.get_serializer(data=serializer_data, context={"user": user})
        serializer.is_valid(raise_exception=True)

        # Save user first, then create teacher
        user.status = "W"  # move to waiting approval after profile completion
        user.save()

        teacher = serializer.save()

        response = {
            "message": "Teacher profile submitted successfully. Awaiting approval.",
            "user_id": user.id,
            "status": user.status,
            "teacher_id": teacher.user_id,
        }
        
        return Response(response, status=status.HTTP_201_CREATED)


class ForgotPasswordAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Yêu cầu đặt lại mật khẩu",
        description=(
            "Gửi mã OTP xác thực cho tài khoản để đặt lại mật khẩu.\n\n"
            "**Yêu cầu:**\n"
            "- Tài khoản phải ở trạng thái V (Verified)\n\n"
            "**Luồng xử lý:**\n"
            "- P (Pending): Gửi OTP xác thực email\n"
            "- I (Incomplete): Yêu cầu hoàn thành hồ sơ\n"
            "- W (Waiting): Chờ phê duyệt từ admin\n"
            "- D (Disabled): Tài khoản bị vô hiệu hóa\n"
            "- V (Verified): Gửi OTP để đặt lại mật khẩu\n\n"
            "**Tham số đầu vào:**\n"
            "- `username_or_email`: Username hoặc email (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="ForgotPasswordRequest",
            fields={
                "username_or_email": serializers.CharField(
                    required=True, help_text="Username hoặc email"
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="OTP sent successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "OTP code has been sent to your email.",
                        },
                        "username": {
                            "type": "string",
                            "example": "john_doe",
                        },
                    },
                    "required": ["message", "username"],
                },
            ),
        },
    )
    def post(self, request):
        username_or_email = request.data.get("username_or_email")

        if not username_or_email:
            return Response(
                {"detail": "Username or email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find user by username or email
        try:
            user = User.objects.get(
                Q(username=username_or_email) | Q(email=username_or_email)
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Account not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check is_active
        if not user.is_active:
            return Response(
                {"detail": "Account is deactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check status - only verified accounts can reset password
        status_code = getattr(user, "status", None)

        if status_code == "P":
            # Resend OTP for registration verification
            otp_code = create_otp_code()
            cache_register_otp(user.id, otp_code, user.email)
            send_registration_otp_email(user.email, otp_code)
            return Response(
                {
                    "detail": "Account is not verified yet. OTP sent to your email.",
                    "status": status_code,
                    "user_id": user.id,
                    "require_verification": True,
                    "redirect_to": f"/verify-otp?user_id={user.id}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_code == "I":
            return Response(
                {
                    "detail": "Please complete your profile first before resetting password.",
                    "status": status_code,
                    "user_id": user.id,
                    "require_certificate": True,
                    "redirect_to": f"/upload-profile?user_id={user.id}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_code == "W":
            return Response(
                {
                    "detail": "Account is pending approval. Please wait for admin review.",
                    "status": status_code,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if status_code == "D":
            return Response(
                {
                    "detail": "Account has been disabled.",
                    "status": status_code,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only status 'V' (Verified) can proceed
        if status_code != "V":
            return Response(
                {"detail": "Account status does not allow password reset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate OTP code
        otp_code = create_otp_code()

        # Cache OTP
        cache_forgot_password_otp(user.username, otp_code)

        # Send OTP email
        send_forgot_password_otp_email(user.username, user.email, otp_code)

        response = {
            "message": "OTP code has been sent to your email.",
            "username": user.username,
        }

        return Response(response, status=status.HTTP_200_OK)


class ForgotPasswordVerifyOTPAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Xác thực OTP đặt lại mật khẩu",
        description=(
            "Xác minh mã OTP và cấp token để đặt lại mật khẩu.\n\n"
            "**Tham số đầu vào:**\n"
            "- `username`: Username (bắt buộc)\n"
            "- `otp_code`: Mã OTP gửi đến email (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="ForgotPasswordVerifyOTPRequest",
            fields={
                "username": serializers.CharField(required=True),
                "otp_code": serializers.CharField(
                    required=True, help_text="Mã OTP gửi đến email"
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="OTP verified successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "OTP verified successfully.",
                        },
                        "reset_token": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "expires_at": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2024-12-15T10:30:00",
                        },
                    },
                    "required": ["message", "reset_token", "expires_at"],
                },
            ),
        },
    )
    def post(self, request):
        username = request.data.get("username")
        otp_code = request.data.get("otp_code")

        if not username or not otp_code:
            return Response(
                {"detail": "Username and OTP code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get OTP from cache
        cache_key = f"forgot_password_{username}"
        cache_data = cache.get(cache_key)

        if not cache_data:
            return Response(
                {"detail": "OTP code has expired or is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_data = json.loads(cache_data)

        # Verify OTP
        if cache_data["otp_code"] != otp_code:
            return Response(
                {"detail": "Invalid OTP code."}, status=status.HTTP_400_BAD_REQUEST
            )

        # OTP verified, delete cache
        cache.delete(cache_key)

        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Generate reset token (JWT RefreshToken)
        reset_token = RefreshToken.for_user(user)

        # Mark token as password reset token
        reset_token["token_type"] = "password_reset"

        # Set expiry time (30 minutes)
        expiry_time = datetime.now() + timedelta(minutes=30)

        response = {
            "message": "OTP verified successfully.",
            "reset_token": str(reset_token),
            "expires_at": expiry_time.isoformat(),
        }

        return Response(response, status=status.HTTP_200_OK)


class ResetPasswordAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Đặt lại mật khẩu",
        description=(
            "Đặt lại mật khẩu mới sau khi xác minh OTP thành công.\n\n"
            "**Yêu cầu:**\n"
            "- Phải cấp reset_token hợp lệ từ `/forgot-password/verify-otp/`\n"
            "- Token hết hạn sau 30 phút\n\n"
            "**Tham số đầu vào:**\n"
            "- `reset_token`: Token nhận từ xác thực OTP (bắt buộc)\n"
            "- `new_password`: Mật khẩu mới (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="ResetPasswordRequest",
            fields={
                "reset_token": serializers.CharField(
                    required=True, help_text="Token từ xác thực OTP"
                ),
                "new_password": serializers.CharField(
                    required=True, write_only=True, help_text="Mật khẩu mới"
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Password reset successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "Password reset successfully. Please login with your new password.",
                        },
                    },
                    "required": ["message"],
                },
            ),
        },
    )
    def post(self, request):
        reset_token = request.data.get("reset_token")
        new_password = request.data.get("new_password")

        if not reset_token or not new_password:
            return Response(
                {"detail": "Reset token and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Decode and verify token
            decoded_token = jwt.decode(
                reset_token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_signature": True},
            )

            # Check token type
            if decoded_token.get("token_type") != "password_reset":
                return Response(
                    {"detail": "Invalid token type for password reset."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get user_id from token
            user_id = decoded_token.get("user_id")

            # Find user
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(new_password)
            user.save()

            # Blacklist token to prevent reuse
            try:
                outstanding_token = OutstandingToken.objects.get(token=reset_token)
                BlacklistedToken.objects.create(token=outstanding_token)
            except OutstandingToken.DoesNotExist:
                pass  # Token might not exist in DB if it's a new token

            return Response(
                {
                    "message": "Password reset successfully. Please login with your new password."
                },
                status=status.HTTP_200_OK,
            )

        except (TokenError, jwt.PyJWTError) as e:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": "Error resetting password."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResendForgotPasswordOTPAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Gửi lại OTP đặt lại mật khẩu",
        description=(
            "Gửi lại mã OTP khi người dùng không nhận được hoặc OTP hết hạn.\n\n"
            "**Tham số đầu vào:**\n"
            "- `username`: Username (bắt buộc)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="ResendForgotPasswordOTPRequest",
            fields={
                "username": serializers.CharField(required=True),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="OTP resent successfully",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {
                            "type": "string",
                            "example": "OTP code has been resent to your email.",
                        },
                    },
                    "required": ["detail"],
                },
            ),
        },
    )
    def post(self, request):
        username = request.data.get("username")

        if not username:
            return Response(
                {"detail": "Username is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            resend_forgot_password_otp_email(username)
            return Response(
                {"detail": "OTP code has been resent to your email."},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Đăng nhập bằng Google",
        description=(
            "Xác thực người dùng thông qua Google OAuth 2.0.\n\n"
            "**Luồng xử lý:**\n"
            "1. Client gửi authorization code từ Google\n"
            "2. Server trao đổi code với Google để lấy access token\n"
            "3. Lấy thông tin user từ Google (email, name, avatar)\n"
            "4. Tạo hoặc cập nhật tài khoản trong hệ thống\n\n"
            "**Response 200 - Student:**\n"
            "- Status V (Verified): Trả về JWT tokens, redirect về home\n"
            "- Status P → V: Tự động chuyển sang Verified và trả về tokens\n\n"
            "**Response 200 - Teacher:**\n"
            "- Status V (Verified): Trả về JWT tokens\n"
            "- Status P → I: Tự động chuyển sang Incomplete, trả về user_id và require_profile=true\n"
            "- Status I: Trả về user_id và require_profile=true, redirect đến upload-profile\n\n"
            "**Response 403:**\n"
            "- Status D: Account disabled\n"
            "- Status W: Waiting for admin approval\n\n"
            "**Tham số đầu vào:**\n"
            "- `code`: Authorization code từ Google (bắt buộc)\n"
            "- `role`: S (Student) hoặc T (Teacher) - mặc định là S (tùy chọn)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="GoogleLoginRequest",
            fields={
                "code": serializers.CharField(
                    required=True, help_text="Authorization code từ Google"
                ),
                "role": serializers.ChoiceField(
                    choices=["S", "T"], required=False, help_text="S=Student, T=Teacher"
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Login successful - Returns tokens or requires profile completion",
                response={
                    "type": "object",
                    "properties": {
                        "access": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "refresh": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["V", "I"],
                            "example": "V",
                        },
                        "username": {"type": "string"},
                        "avatar": {"type": "string", "nullable": True},
                        "user_id": {"type": "integer", "nullable": True},
                        "role": {"type": "string"},
                        "require_profile": {"type": "boolean", "nullable": True},
                    },
                },
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        # one-time code from Google when user clicks "Sign in with Google"
        code = request.data.get("code")

        if not code:
            return Response(
                {"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # send code to Google to get access token
        google_token_url = "https://oauth2.googleapis.com/token"
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.OAUTH2_GOOGLE_REDIRECT_URI,
            "client_id": settings.OAUTH2_GOOGLE_KEY,
            "client_secret": settings.OAUTH2_GOOGLE_SECRET,
        }

        try:
            token_response = requests.post(google_token_url, data=params, timeout=10)
            print(token_response.json())
        except requests.RequestException:
            return Response(
                {"error": "Failed to connect to Google"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if token_response.status_code != 200:
            return Response(
                {"error": "Failed to exchange code for token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_access_token = token_response.json().get("access_token")

        if not google_access_token:
            return Response(
                {"error": "No access token received from Google"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # get user info from Google
        google_user_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        try:
            user_response = requests.get(
                google_user_url,
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10,
            )
        except requests.RequestException:
            return Response(
                {"error": "Failed to fetch user info from Google"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if user_response.status_code != 200:
            return Response(
                {"error": "Failed to get user information"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_data = user_response.json()

        email = google_data.get("email")
        full_name = google_data.get("name")
        avatar_url = google_data.get("picture")

        if not email:
            return Response(
                {"error": "Email is required from Google account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get role from request (can be passed via state parameter in OAuth URL)
        # Default to Student if not specified
        role = request.data.get("role", "S").upper()
        if role not in ["S", "T"]:
            role = "S"  # Default to Student if invalid role

        # Check if user exists by email
        try:
            user = User.objects.get(email=email)

            # Branch by role for existing user
            if user.role == "A":
                # Admin login flow - only allow status V
                if user.status != "V":
                    return Response(
                        {"error": "Please contact the development team for assistance."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                # Admin with status V -> return tokens
                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar, request),
                }
                return Response(response_data, status=status.HTTP_200_OK)

            if user.role == "S":
                # Student flow
                if user.status == "D":
                    return Response(
                        {"error": "Account has been disabled"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if user.status == "P":
                    user.status = "V"
                    user.save()
                # status V -> return tokens
                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar, request),
                }
                return Response(response_data, status=status.HTTP_200_OK)

            elif user.role == "T":
                # Teacher flow
                if user.status == "D":
                    return Response(
                        {"error": "Account has been disabled"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if user.status == "W":
                    return Response(
                        {
                            "error": "Your account is waiting for admin approval. Please wait."
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if user.status == "P":
                    # move to incomplete profile
                    user.status = "I"
                    user.save()
                    return Response(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "role": user.role,
                            "status": user.status,
                            "require_profile": True,
                        },
                        status=status.HTTP_200_OK,
                    )
                # status I -> require profile completion, no tokens
                if user.status == "I":
                    return Response(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "role": user.role,
                            "status": user.status,
                            "require_profile": True,
                        },
                        status=status.HTTP_200_OK,
                    )
                if user.status == "V":
                    refresh = RefreshToken.for_user(user)
                    refresh["role"] = user.role
                    response_data = {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "status": user.status,
                        "username": user.username,
                        "avatar": get_absolute_media_url(user.avatar, request),
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                # any other unexpected status
                return Response(
                    {
                        "error": "Account is not in a valid state. Please contact support."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        except User.DoesNotExist:
            # Create a new user
            base_username = email.split("@")[0]
            unique_username = generate_unique_username(base_username)

            user = User.objects.create_user(
                username=unique_username,
                email=email,
                full_name=full_name or "",
                password=None,  # Social login users don't need a password
            )

            # Set role and status based on user type
            user.role = role
            if role == "S":
                # Student: Verified status, can login immediately
                user.status = "V"

                # Download and save avatar
                if avatar_url:
                    avatar_path = download_and_save_avatar(avatar_url, user)
                    if avatar_path:
                        user.avatar = avatar_path

                user.save()

                # Create Student instance
                Student.objects.create(user=user)

                # Generate JWT tokens for verified student
                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role

                response_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar, request),
                }

                return Response(response_data, status=status.HTTP_200_OK)


class FacebookLoginAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Đăng nhập bằng Facebook",
        description=(
            "Xác thực người dùng thông qua Facebook OAuth 2.0.\n\n"
            "**Luồng xử lý:**\n"
            "1. Client gửi authorization code từ Facebook\n"
            "2. Server trao đổi code với Facebook để lấy access token\n"
            "3. Lấy thông tin user từ Facebook (email, name, avatar)\n"
            "4. Tạo hoặc cập nhật tài khoản trong hệ thống\n\n"
            "**Response 200 - Student:**\n"
            "- Status V (Verified): Trả về JWT tokens, redirect về home\n"
            "- Status P → V: Tự động chuyển sang Verified và trả về tokens\n\n"
            "**Response 200 - Teacher:**\n"
            "- Status V (Verified): Trả về JWT tokens\n"
            "- Status P → I: Tự động chuyển sang Incomplete, trả về user_id và require_profile=true\n"
            "- Status I: Trả về user_id và require_profile=true, redirect đến upload-profile\n\n"
            "**Response 403:**\n"
            "- Status D: Account disabled\n"
            "- Status W: Waiting for admin approval\n\n"
            "**Tham số đầu vào:**\n"
            "- `code`: Authorization code từ Facebook (bắt buộc)\n"
            "- `role`: S (Student) hoặc T (Teacher) - mặc định là S (tùy chọn)"
        ),
        tags=["accounts"],
        request=inline_serializer(
            name="FacebookLoginRequest",
            fields={
                "code": serializers.CharField(
                    required=True, help_text="Authorization code từ Facebook"
                ),
                "role": serializers.ChoiceField(
                    choices=["S", "T"], required=False, help_text="S=Student, T=Teacher"
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Login successful - Returns tokens or requires profile completion",
                response={
                    "type": "object",
                    "properties": {
                        "access": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "refresh": {
                            "type": "string",
                            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["V", "I"],
                            "example": "V",
                        },
                        "username": {"type": "string"},
                        "avatar": {"type": "string", "nullable": True},
                        "user_id": {"type": "integer", "nullable": True},
                        "role": {"type": "string"},
                        "require_profile": {"type": "boolean", "nullable": True},
                    },
                },
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        # One-time code from Facebook OAuth
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Exchange code for access token
        token_url = "https://graph.facebook.com/v17.0/oauth/access_token"
        params = {
            "client_id": settings.OAUTH2_FACEBOOK_KEY,
            "redirect_uri": settings.OAUTH2_FACEBOOK_REDIRECT_URI,
            "client_secret": settings.OAUTH2_FACEBOOK_SECRET,
            "code": code,
        }
        try:
            token_response = requests.get(token_url, params=params, timeout=10)
        except requests.RequestException:
            return Response(
                {"error": "Failed to connect to Facebook"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if token_response.status_code != 200:
            return Response(
                {"error": "Failed to exchange code for token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = token_response.json().get("access_token")
        if not access_token:
            return Response(
                {"error": "No access token received from Facebook"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch user info
        user_info_url = "https://graph.facebook.com/me"
        user_params = {"fields": "id,name,email,picture", "access_token": access_token}
        try:
            user_response = requests.get(user_info_url, params=user_params, timeout=10)
        except requests.RequestException:
            return Response(
                {"error": "Failed to fetch user info from Facebook"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if user_response.status_code != 200:
            return Response(
                {"error": "Failed to get user information"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fb_data = user_response.json()
        email = fb_data.get("email")
        full_name = fb_data.get("name")
        picture_data = fb_data.get("picture", {}).get("data", {})
        avatar_url = picture_data.get("url")

        if not email:
            return Response(
                {"error": "Email is required from Facebook account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = request.data.get("role", "S").upper()
        if role not in ["S", "T"]:
            role = "S"

        try:
            user = User.objects.get(email=email)

            if user.role == "A":
                # Admin login flow - only allow status V
                if user.status != "V":
                    return Response(
                        {"error": "Please contact the development team for assistance."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                # Admin with status V -> return tokens
                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar, request),
                }
                return Response(response_data, status=status.HTTP_200_OK)

            if user.role == "S":
                if user.status == "D":
                    return Response(
                        {"error": "Account has been disabled"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if user.status == "P":
                    user.status = "V"
                    user.save()

                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar, request),
                }
                return Response(response_data, status=status.HTTP_200_OK)

            elif user.role == "T":
                if user.status == "D":
                    return Response(
                        {"error": "Account has been disabled"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if user.status == "W":
                    return Response(
                        {
                            "error": "Your account is waiting for admin approval. Please wait."
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if user.status == "P":
                    user.status = "I"
                    user.save()
                    return Response(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "role": user.role,
                            "status": user.status,
                            "require_profile": True,
                        },
                        status=status.HTTP_200_OK,
                    )
                if user.status == "I":
                    return Response(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "role": user.role,
                            "status": user.status,
                            "require_profile": True,
                        },
                        status=status.HTTP_200_OK,
                    )
                if user.status == "V":
                    refresh = RefreshToken.for_user(user)
                    refresh["role"] = user.role
                    response_data = {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "status": user.status,
                        "username": user.username,
                        "avatar": get_absolute_media_url(user.avatar, request),
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                return Response(
                    {
                        "error": "Account is not in a valid state. Please contact support."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        except User.DoesNotExist:
            base_username = email.split("@")[0]
            unique_username = generate_unique_username(base_username)

            user = User.objects.create_user(
                username=unique_username,
                email=email,
                full_name=full_name or "",
                password=None,
            )
            user.role = role

            if role == "S":
                user.status = "V"

                if avatar_url:
                    avatar_path = download_and_save_avatar(avatar_url, user)
                    if avatar_path:
                        user.avatar = avatar_path
                user.save()
                Student.objects.create(user=user)

                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar, request),
                }
                return Response(response_data, status=status.HTTP_200_OK)

            elif role == "T":
                user.status = "I"

                if avatar_url:
                    avatar_path = download_and_save_avatar(avatar_url, user)
                    if avatar_path:
                        user.avatar = avatar_path
                user.save()

                response_data = {
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "status": user.status,
                    "avatar": get_absolute_media_url(user.avatar, request),
                    "require_profile": True,
                }
                return Response(response_data, status=status.HTTP_200_OK)

        return Response({"error": "Unhandled flow"}, status=status.HTTP_400_BAD_REQUEST)


class AdminUserPagination(PageNumberPagination):
    """
    Pagination class for Admin Users API
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminUsersManagementAPIView(generics.GenericAPIView):
    """
    Admin Users Management API - Manage users and pending approvals
    
    Supports multiple HTTP methods:
    - GET: List users with filtering and pagination
    - Future methods will be added here (PATCH, DELETE, etc.)
    """
    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = AdminUserFilter
    pagination_class = AdminUserPagination
    lookup_field = 'pk'
    lookup_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        """
        GET method - Route to list or retrieve based on URL pattern
        """
        # If pk is in kwargs, this is a retrieve request
        if 'pk' in kwargs:
            return self.retrieve(request, pk=kwargs.get('pk'))
        
        # Otherwise, this is a list request
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Order by date_joined (newest first)
        queryset = queryset.order_by('-date_joined')
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Add additional fields for admin list view
            data = self._add_admin_list_fields(serializer.data)
            return self.get_paginated_response(data)
        
        # If no pagination, return all (shouldn't happen with pagination_class set)
        serializer = self.get_serializer(queryset, many=True)
        data = self._add_admin_list_fields(serializer.data)
        return Response(data, status=status.HTTP_200_OK)

    def _add_admin_list_fields(self, data_list):
        """
        Add role_display, status_display, avatar_url to each user in list
        """
        request = self.request
        for item in data_list:
            # Add role_display
            role = item.get('role', '')
            role_display_map = {'S': 'Student', 'T': 'Teacher', 'A': 'Admin'}
            item['role_display'] = role_display_map.get(role, '')
            
            # Add status_display
            status = item.get('status', '')
            status_display_map = {
                'P': 'Pending Verification',
                'I': 'Incomplete Profile',
                'W': 'Waiting Approval',
                'V': 'Verified',
                'D': 'Disabled'
            }
            item['status_display'] = status_display_map.get(status, '')
            
            # Add avatar_url (convert avatar field to avatar_url with absolute URL)
            avatar = item.get('avatar')
            item['avatar_url'] = get_absolute_media_url(avatar, request)
            # Remove avatar field if exists (keep only avatar_url)
            item.pop('avatar', None)
        
        return data_list

    def get_queryset(self):
        """
        Get queryset - can be overridden for custom filtering
        """
        return User.objects.all()

    def get_serializer_context(self):
        """
        Add request to serializer context for building absolute URLs
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, pk=None):
        """
        Retrieve detailed information of a teacher user
        Only teachers (role='T') can be viewed
        """
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is a teacher
        if user.role != 'T':
            return Response(
                {"error": "You can only view teacher information"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user data
        user_serializer = UserSerializer(user, context={'request': request})
        user_data = user_serializer.data
        
        # Get teacher data
        try:
            teacher = user.teacher
            teacher_serializer = TeacherSerializer(teacher, context={'request': request})
            teacher_data = teacher_serializer.data
            
            # Process credentials to absolute URLs
            credentials = teacher_data.get('credentials', {})
            if credentials and 'certificates' in credentials:
                certificates = credentials['certificates']
                processed_certificates = []
                for cert in certificates:
                    cert_url = cert.get('url', '')
                    if cert_url:
                        absolute_url = get_absolute_media_url(cert_url, request)
                        processed_cert = cert.copy()
                        processed_cert['url'] = absolute_url
                        processed_certificates.append(processed_cert)
                    else:
                        processed_certificates.append(cert)
                credentials['certificates'] = processed_certificates
                teacher_data['credentials'] = credentials
        except Teacher.DoesNotExist:
            teacher_data = {}

        # Combine user and teacher data
        response_data = user_data.copy()
        response_data.update(teacher_data)
        
        # Add display fields
        response_data['role_display'] = user.get_role_display()
        response_data['status_display'] = user.get_status_display()
        if hasattr(user, 'teacher'):
            response_data['teacher_type_display'] = user.teacher.get_teacher_type_display()
        
        # Convert avatar to avatar_url using helper function
        avatar = response_data.get('avatar')
        response_data['avatar_url'] = get_absolute_media_url(avatar, request)
        response_data.pop('avatar', None)
        
        return Response(response_data, status=status.HTTP_200_OK)