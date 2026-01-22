from ..models import User
from ..serializers import (
    UserSerializer,
    StudentSerializer,
    TeacherSerializer,
)
from ..utils import (
    create_otp_code,
    cache_register_otp,
    send_registration_otp_email,
    resend_registration_otp_email,
    verify_registration_otp,
    delete_registration_otp_cache,
    process_credential_files_upload,
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer,
)

from rest_framework import serializers
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class UserRegistrationAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserSerializer

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

        if role not in ["S", "T"]:
            return Response(
                {"detail": "Invalid role. Must be 'S' (Student) or 'T' (Teacher)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_serializer = UserSerializer(data=request.data)

        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = user_serializer.save()
        otp_code = create_otp_code()

        cache_register_otp(user.id, otp_code, user.email)
        send_registration_otp_email(user.email, otp_code)

        role_name = "Student" if role == "S" else "Teacher"
        response = {
            "message": f"{role_name} account registered successfully. Please check your email to verify your account.",
            "user_id": user.id,
        }

        return Response(response, status=status.HTTP_201_CREATED)

class VerifyRegistrationOTPAPIView(generics.CreateAPIView):
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

        try:
            verify_registration_otp(user_id, otp_code)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id, status="P")
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found or already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.role == "S":
            user.status = "V"
        elif user.role == "T":
            user.status = "I"
        else:
            return Response({"detail": "Invalid user role."}, status=status.HTTP_400_BAD_REQUEST)

        user.save()
        delete_registration_otp_cache(user_id)

        role_name = "Student" if user.role == "S" else "Teacher"

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

class ResendRegistrationOTPAPIView(generics.CreateAPIView):
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

        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response({"detail": "user_id must be a valid integer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            resend_registration_otp_email(user.id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = {"message": "OTP code has been resent to your email."}

        return Response(response, status=status.HTTP_200_OK)

class TeacherSubmitProfileAPIView(generics.CreateAPIView):
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
        user_id = request.data.get("user_id")

        if not user_id:
            return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response({"detail": "user_id must be a valid integer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id, role="T")
        except User.DoesNotExist:
            return Response({"detail": "Teacher not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.status != "I":
            return Response({"detail": "Profile already completed or not allowed."}, status=status.HTTP_400_BAD_REQUEST)

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

        user.full_name = full_name
        user.date_of_birth = date_of_birth
        user.avatar = avatar_file
        
        try:
            credentials_data = process_credential_files_upload(request.FILES, user)
        except ValueError as e:
            return Response({"credentials": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer_data = {
            "current_workplace": request.data.get("current_workplace", "").strip(),
            "teacher_type": request.data.get("teacher_type"),
            "experience_year": request.data.get("experience_year"),
            "introduction": request.data.get("introduction", "").strip(),
            "credentials": credentials_data,
        }

        serializer = self.get_serializer(data=serializer_data, context={"user": user})
        serializer.is_valid(raise_exception=True)

        user.status = "W"
        user.save()
        teacher = serializer.save()
        response = {
            "message": "Teacher profile submitted successfully. Awaiting approval.",
            "user_id": user.id,
            "status": user.status,
            "teacher_id": teacher.user_id,
        }

        return Response(response, status=status.HTTP_201_CREATED)
