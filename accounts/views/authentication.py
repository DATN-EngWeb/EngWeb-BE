from ..models import User, Student
from ..serializers import CustomTokenObtainPairSerializer
from ..utils import (
    download_and_save_avatar,
    generate_unique_username,
    get_absolute_media_url,
)

from django.conf import settings
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers

import requests

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="Login to account",
        description=(
            "Authenticate user and generate JWT tokens.\n\n"
            "**Processing based on account status:**\n\n"
            "- **P (Pending Verification)**: Send OTP verification email, require verification\n"
            "- **I (Incomplete Profile)**: Teacher incomplete profile, require upload certificate\n"
            "- **W (Waiting Approval)**: Waiting for admin approval, no tokens\n"
            "- **V (Verified)**: Generate access token and refresh token\n"
            "- **D (Disabled)**: Account disabled, no login allowed\n\n"
            "**Input parameters:**\n"
            "- `username`: username or email\n"
            "- `password`: password"
        ),
        tags=["authentication"],
        request=CustomTokenObtainPairSerializer,
        examples=[
            OpenApiExample(
                name="Admin login",
                request_only=True,
                value={
                    "username": "admin",
                    "password": "admin",
                },
            ),
        ],
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
                examples=[
                    OpenApiExample(
                        name="Admin login",
                        value={
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2OTQxODA2NSwiaWF0IjoxNzY5MzMxNjY1LCJqdGkiOiI2NWU4MzQyZjE0MDE0NWViOGZlZmJjMzkyMGFlZDE3NiIsInVzZXJfaWQiOiIxIiwicm9sZSI6IkEifQ.UrZ1gYfd16hXPoR_QxWh1HmPDc0YqgrBqhBAULu-qaU",
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY5NTExNjY1LCJpYXQiOjE3NjkzMzE2NjUsImp0aSI6IjhjNzUyMjVlYjY2NDRiOTA5YTU4MDM1NmIzZTI2YzE4IiwidXNlcl9pZCI6IjEiLCJyb2xlIjoiQSJ9.692YKwbTbJvpQKUvcI8GLuiJqa9HBUxnuc_YUlZvU4Y",
                            "status": "V",
                            "username": "admin",
                            "avatar": "https://storage.googleapis.com/dev-nens-english-app-test-vu/users/avatars/admin-avatar.png",
                        },
                    ),
                ],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class LogoutAPIView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Logout account",
        description=(
            "Logout user by blacklisting refresh token.\n\n"
            "**Requirements:**\n"
            "- Must be authenticated (valid refresh token)\n"
            "- Send refresh token to blacklist\n\n"
            "**Input parameters:**\n"
            "- `refresh`: Refresh token to blacklist (required)"
        ),
        tags=["authentication"],
        request=inline_serializer(
            name="LogoutRequest",
            fields={
                "refresh": serializers.CharField(
                    required=True,
                ),
            },
        ),
        examples=[
            OpenApiExample(
                name="Logout",
                request_only=True,
                value={
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2OTQxODM3NCwiaWF0IjoxNzY5MzMxOTc0LCJqdGkiOiI1OGFlYjNkZjc0NzI0OGY5YjZlMDQ0NzU3ZDYxMGQ1YiIsInVzZXJfaWQiOiIxIiwicm9sZSI6IkEifQ.D7-gBPucYaHgLTo1SCwzcFK3L35xypTZbzvc3PwzvmA",
                },
            ),
        ],
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
                examples=[
                    OpenApiExample(
                        name="Logout",
                        value={
                            "message": "Logged out successfully",
                        },
                    ),
                ],
            ),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        
        if not refresh_token:
            return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class GoogleLoginAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Login with Google",
        description=(
            "Authenticate user through Google OAuth 2.0.\n\n"
            "**Processing:**\n"
            "1. Client sends authorization code from Google\n"
            "2. Server exchanges code with Google to get access token\n"
            "3. Get user info from Google (email, name, avatar)\n"
            "4. Create or update account in the system\n\n"
            "**Response 200 - Student:**\n"
            "- Status V (Verified): Return JWT tokens, redirect to home\n"
            "- Status P → V: Automatically change to Verified and return tokens\n\n"
            "**Response 200 - Teacher:**\n"
            "- Status V (Verified): Return JWT tokens\n"
            "- Status P → I: Automatically change to Incomplete and return user_id and require_profile=true\n"
            "- Status I: Return user_id and require_profile=true, redirect to upload-profile\n\n"
            "**Response 403:**\n"
            "- Status D: Account disabled\n"
            "- Status W: Waiting for admin approval\n\n"
            "**Input parameters:**\n"
            "- `code`: Authorization code from Google (required)\n"
            "- `role`: S (Student) or T (Teacher) - default is S (optional)"
        ),
        tags=["authentication"],
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
            return Response({"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST)

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
        except requests.RequestException:
            return Response({"error": "Failed to connect to Google"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if token_response.status_code != 200:
            return Response({"error": "Failed to exchange code for token"}, status=status.HTTP_400_BAD_REQUEST)

        google_access_token = token_response.json().get("access_token")

        if not google_access_token:
            return Response({"error": "No access token received from Google"}, status=status.HTTP_400_BAD_REQUEST)

        # get user info from Google
        google_user_url = "https://www.googleapis.com/oauth2/v2/userinfo"

        try:
            user_response = requests.get(
                google_user_url,
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10
            )
        except requests.RequestException:
            return Response({"error": "Failed to fetch user info from Google"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if user_response.status_code != 200:
            return Response({"error": "Failed to get user information"}, status=status.HTTP_400_BAD_REQUEST)

        google_data = user_response.json()
        email = google_data.get("email")
        full_name = google_data.get("name")
        avatar_url = google_data.get("picture")

        if not email:
            return Response({"error": "Email is required from Google account"}, status=status.HTTP_400_BAD_REQUEST)

        role = request.data.get("role", "S").upper()
        if role not in ["S", "T"]:
            role = "S"

        # check if user exists by email
        try:
            user = User.objects.get(email=email)

            if user.status == "D":
                return Response({"error": "Account has been disabled"}, status=status.HTTP_403_FORBIDDEN)

            # admin
            if user.role == "A":
                if user.status != "V":
                    return Response({"error": "Please contact the development team for assistance."}, status=status.HTTP_403_FORBIDDEN)

                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar)
                }

                return Response(response, status=status.HTTP_200_OK)

            # student
            if user.role == "S":
                if user.status == "P":
                    user.status = "V"
                    user.save()

                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar)
                }

                return Response(response, status=status.HTTP_200_OK)

            elif user.role == "T":
                # teacher
                if user.status == "W":
                    return Response({"error": "Your account is waiting for admin approval."}, status=status.HTTP_403_FORBIDDEN)
                
                if user.status == "P":
                    # move to incomplete profile
                    user.status = "I"
                    user.save()

                    response = {
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "status": user.status,
                        "require_profile": True,
                    }

                    return Response(response, status=status.HTTP_200_OK)

                # status I -> require profile completion, no tokens
                if user.status == "I":
                    response = {
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "status": user.status,
                        "require_profile": True,
                    }

                    return Response(response, status=status.HTTP_200_OK)

                if user.status == "V":
                    refresh = RefreshToken.for_user(user)
                    refresh["role"] = user.role

                    response = {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "status": user.status,
                        "username": user.username,
                        "avatar": get_absolute_media_url(user.avatar)
                    }
                    return Response(response, status=status.HTTP_200_OK)

                # any other unexpected status
                return Response({"error": "Account is not in a valid state."}, status=status.HTTP_403_FORBIDDEN)

        except User.DoesNotExist:
            # Create a new user
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

                response = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar)
                }

                return Response(response, status=status.HTTP_200_OK)

            elif role == "T":
                user.status = "I"

                if avatar_url:
                    avatar_path = download_and_save_avatar(avatar_url, user)
                    if avatar_path:
                        user.avatar = avatar_path

                user.save()

                response = {
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "status": user.status,
                    "avatar": get_absolute_media_url(user.avatar),
                    "require_profile": True
                }

                return Response(response, status=status.HTTP_200_OK)

class FacebookLoginAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Login with Facebook",
        description=(
            "Authenticate user through Facebook OAuth 2.0.\n\n"
            "**Luồng xử lý:**\n"
            "1. Client sends authorization code from Facebook\n"
            "2. Server exchanges code with Facebook to get access token\n"
            "3. Get user info from Facebook (email, name, avatar)\n"
            "4. Create or update account in the system\n\n"
            "**Response 200 - Student:**\n"
            "- Status V (Verified): Return JWT tokens, redirect to home\n"
            "- Status P → V: Automatically change to Verified and return tokens\n\n"
            "**Response 200 - Teacher:**\n"
            "- Status V (Verified): Return JWT tokens\n"
            "- Status P → I: Automatically change to Incomplete and return user_id and require_profile=true\n"
            "- Status I: Return user_id and require_profile=true, redirect to upload-profile\n\n"
            "**Response 403:**\n"
            "- Status D: Account disabled\n"
            "- Status W: Waiting for admin approval\n\n"
            "**Input parameters:**\n"
            "- `code`: Authorization code from Facebook (required)\n"
            "- `role`: S (Student) or T (Teacher) - default is S (optional)"
        ),
        tags=["authentication"],
        request=inline_serializer(
            name="FacebookLoginRequest",
            fields={
                "code": serializers.CharField(
                    required=True, help_text="Authorization code from Facebook"
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
        code = request.data.get("code")

        if not code:
            return Response({"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"error": "Failed to connect to Facebook"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if token_response.status_code != 200:
            return Response({"error": "Failed to exchange code for token"}, status=status.HTTP_400_BAD_REQUEST)

        access_token = token_response.json().get("access_token")
        if not access_token:
            return Response({"error": "No access token received from Facebook"}, status=status.HTTP_400_BAD_REQUEST)

        user_info_url = "https://graph.facebook.com/me"
        user_params = {"fields": "id,name,email,picture", "access_token": access_token}

        try:
            user_response = requests.get(user_info_url, params=user_params, timeout=10)
        except requests.RequestException:
            return Response({"error": "Failed to fetch user info from Facebook"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if user_response.status_code != 200:
            return Response({"error": "Failed to get user information"}, status=status.HTTP_400_BAD_REQUEST)

        fb_data = user_response.json()
        email = fb_data.get("email")
        full_name = fb_data.get("name")
        picture_data = fb_data.get("picture", {}).get("data", {})
        avatar_url = picture_data.get("url")

        if not email:
            return Response({"error": "Email is required from Facebook account"}, status=status.HTTP_400_BAD_REQUEST)

        role = request.data.get("role", "S").upper()
        
        if role not in ["S", "T"]:
            role = "S"

        try:
            user = User.objects.get(email=email)

            if user.status == "D":
                return Response({"error": "Account has been disabled"}, status=status.HTTP_403_FORBIDDEN)

            if user.role == "A":
                if user.status != "V":
                    return Response({"error": "Please contact the development team for assistance."}, status=status.HTTP_403_FORBIDDEN)

                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar)
                }

                return Response(response, status=status.HTTP_200_OK)

            if user.role == "S":
                if user.status == "P":
                    user.status = "V"
                    user.save()

                refresh = RefreshToken.for_user(user)
                refresh["role"] = user.role
                response = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar)
                }

                return Response(response, status=status.HTTP_200_OK)

            elif user.role == "T":
                if user.status == "W":
                    return Response({"error": "Your account is waiting for admin approval. Please wait."}, status=status.HTTP_403_FORBIDDEN)

                if user.status == "P":
                    user.status = "I"
                    user.save()
                    response = {
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "status": user.status,
                        "require_profile": True,
                    }

                    return Response(response, status=status.HTTP_200_OK)
                if user.status == "I":
                    response = {
                        "user_id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "status": user.status,
                        "require_profile": True,
                    }

                    return Response(response, status=status.HTTP_200_OK)

                if user.status == "V":
                    refresh = RefreshToken.for_user(user)
                    refresh["role"] = user.role
                    response = {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "status": user.status,
                        "username": user.username,
                        "avatar": get_absolute_media_url(user.avatar)
                    }
                    return Response(response, status=status.HTTP_200_OK)

                return Response({"error": "Account is not in a valid state. Please contact support."}, status=status.HTTP_403_FORBIDDEN)

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
                response = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "status": user.status,
                    "username": user.username,
                    "avatar": get_absolute_media_url(user.avatar)
                }

                return Response(response, status=status.HTTP_200_OK)

            elif role == "T":
                user.status = "I"

                if avatar_url:
                    avatar_path = download_and_save_avatar(avatar_url, user)
                    if avatar_path:
                        user.avatar = avatar_path
                user.save()

                response = {
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "status": user.status,
                    "avatar": get_absolute_media_url(user.avatar),
                    "require_profile": True
                }

                return Response(response, status=status.HTTP_200_OK)

        return Response({"error": "Unhandled flow"}, status=status.HTTP_400_BAD_REQUEST)
