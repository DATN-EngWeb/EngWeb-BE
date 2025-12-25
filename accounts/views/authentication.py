from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.conf import settings
import requests
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User, Student
from ..serializers import CustomTokenObtainPairSerializer
from ..utils import (
    download_and_save_avatar,
    generate_unique_username,
    get_absolute_media_url,
)
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers


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

            elif role == "T":
                # Teacher: Incomplete status, require profile completion
                user.status = "I"

                # Download and save avatar
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