from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import jwt
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from ..models import User
from ..utils import (
    create_otp_code,
    cache_register_otp,
    send_registration_otp_email,
    cache_forgot_password_otp,
    send_forgot_password_otp_email,
    resend_forgot_password_otp_email,
)
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers


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

