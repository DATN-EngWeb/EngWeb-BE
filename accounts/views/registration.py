from ..models import User
from ..serializers import UserSerializer, TeacherSerializer
from ..utils import (
    create_otp_code,
    cache_register_otp,
    send_registration_otp_email,
    resend_registration_otp_email,
    verify_registration_otp,
    delete_registration_otp_cache,
    process_credential_files_upload
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)

from rest_framework import serializers
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

class UserRegistrationAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @extend_schema(
        summary="Register a new user and send verification email",
        description=(
            "1. Get `role` from request(`S` = Student, `T` = Teacher).\n"
            "2. Create a new user with status `P` (Pending Verification).\n"
            "3. Create a new OTP code and cache it.\n"
            "4. Send verification email to the user.\n"
            "5. Return the `user_id` for next step(Verify Registration OTP).\n"
        ),
        tags=["registration"],
        request=inline_serializer(
            name="UserRegistrationRequest",
            fields={
                "username": serializers.CharField(required=True),
                "email": serializers.EmailField(required=True),
                "password": serializers.CharField(required=True),
                "role": serializers.ChoiceField(choices=["S", "T"], required=True),
            },
        ),
        examples=[
            OpenApiExample(
                name="Student registration",
                value={
                    "username": "student",
                    "email": "vulocninh1@gmail.com",
                    "password": "Student123@",
                    "role": "S",
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Teacher registration",
                value={
                    "username": "teacher",
                    "email": "vulopd7cbl@gmail.com",
                    "password": "Teacher123@",
                    "role": "T",
                },
                request_only=True,
            ),
        ],
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
                        "user_id": {"type": "integer", "example": 2},
                    },
                    "required": ["message", "user_id"],
                },
                examples=[
                    OpenApiExample(
                        name="Student registration",
                        value={
                            "message": "Student account registered successfully. Please check your email to verify your account.",
                            "user_id": 2,
                        },
                    ),
                    OpenApiExample(
                        name="Teacher registration",
                        value={
                            "message": "Teacher account registered successfully. Please check your email to verify your account.",
                            "user_id": 3,
                        },
                    ),
                ],
            )
        },
    )
    def post(self, request):
        role = request.data.get("role", "").upper()

        if role not in ["S", "T"]:
            return Response(
                {"detail": "Invalid role. Must be 'S' (Student) or 'T' (Teacher)."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user_serializer = UserSerializer(data=request.data)

        if not user_serializer.is_valid():
            return Response(
                user_serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
        summary="Verify registration OTP and update user status",
        description=(
            "1. Verify the OTP code.\n"
            "2. Update the user status based on the role.\n"
            "- Teacher = `I` (Incomplete Profile)\n"
            "- Student = `V` (Verified)\n"
            "3. Delete the OTP code from cache\n"
            "4. Return the `user_id` and `status`."
        ),
        tags=["registration"],
        request=inline_serializer(
            name="VerifyRegistrationOTPRequest",
            fields={
                "user_id": serializers.IntegerField(required=True),
                "otp_code": serializers.CharField(
                    required=True, help_text="OTP code sent to email"
                ),
            },
        ),
        examples=[
            OpenApiExample(
                name="Student verify OTP",
                request_only=True,
                value={"user_id": 2, "otp_code": "137583"},
            ),
            OpenApiExample(
                name="Teacher verify OTP",
                request_only=True,
                value={"user_id": 3, "otp_code": "690169"},
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="OTP verified successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "user_id": {"type": "integer"},
                        "status": {"type": "string", "enum": ["V", "I"]},
                    },
                    "required": ["message", "user_id", "status"],
                },
                examples=[
                    OpenApiExample(
                        name="Student verify OTP",
                        value={
                            "message": "Student account verified successfully.",
                            "user_id": 2,
                            "status": "V",
                        },
                    ),
                    OpenApiExample(
                        name="Teacher verify OTP",
                        value={
                            "message": "Teacher account verified successfully.",
                            "user_id": 3,
                            "status": "I",
                        },
                    ),
                ],
            ),
        },
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        otp_code = request.data.get("otp_code")

        try:
            verify_registration_otp(user_id, otp_code)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
            return Response(
                {"detail": "Invalid user role."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user.save()
        delete_registration_otp_cache(user_id)

        role_name = "Student" if user.role == "S" else "Teacher"
        response = {
            "message": f"{role_name} account verified successfully.",
            "user_id": user.id,
            "status": user.status
        }

        return Response(response, status=status.HTTP_200_OK)

class ResendRegistrationOTPAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Resend registration OTP",
        description=(
            "1. Get `user_id` from request.\n"
            "2. Resend the OTP code to the user's email.\n"
            "3. Return the `message`."
        ),
        tags=["registration"],
        request=inline_serializer(
            name="ResendRegistrationOTPRequest",
            fields={
                "user_id": serializers.IntegerField(required=True),
            },
        ),
        examples=[
            OpenApiExample(
                name="Request example",
                value={"user_id": 2},
                request_only=True,
            ),
            OpenApiExample(
                name="Success response",
                value={"message": "OTP code has been resent to your email."},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                name="Rate limit error response",
                value={"detail": "Please wait at least 1 minute before requesting a new OTP code."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="OTP resent successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    },
                    "required": ["message"],
                },
            ),
            400: OpenApiResponse(
                description="Validation error (e.g., rate limit)",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"},
                    },
                },
            ),
        },
    )
    def post(self, request):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

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
        summary="OTP Verification (I - Incomplete Profile) -> Teacher Submit Profile (W - Waiting Approval)",
        description=(
            "**Parameters (multipart/form-data):**\n"
            "- `user.id`: User ID (required)\n"
            "- `user.full_name`: Full name (required)\n"
            "- `user.date_of_birth`: Date of birth (YYYY-MM-DD, required)\n"
            "- `user.avatar`: Avatar (required)\n"
            "- `teacher.current_workplace`: Current workplace (required)\n"
            "- `teacher.teacher_type`: Teacher type - S (School), C (Center), F (Freelance) (required)\n"
            "- `teacher.experience_year`: Experience year (required)\n"
            "- `teacher.introduction`: Introduction (required)\n"
            "- `teacher.credentials`: Credentials (can upload multiple files, required at least 1)"
        ),
        tags=["registration"],
        request=inline_serializer(
            name="TeacherProfileRequest",
            fields={
                "user.id": serializers.IntegerField(required=True),
                "user.full_name": serializers.CharField(required=True),
                "user.date_of_birth": serializers.DateField(required=True),
                "user.avatar": serializers.FileField(required=True),
                "teacher.current_workplace": serializers.CharField(required=True),
                "teacher.teacher_type": serializers.ChoiceField(choices=["S", "C", "F"], required=True),
                "teacher.experience_year": serializers.IntegerField(required=True),
                "teacher.introduction": serializers.CharField(required=True),
                "teacher.credentials": serializers.ListField(child=serializers.FileField(), required=True),
            },
        ),
        examples=[
            OpenApiExample(
                name="Submit teacher profile example",
                value={
                    "user.id": 2,
                    "user.full_name": "Nguyễn Hoàng Vũ",
                    "user.date_of_birth": "2004-09-03",
                    "teacher.current_workplace": "Pizza 4P's",
                    "teacher.teacher_type": "C",
                    "teacher.experience_year": 1,
                    "teacher.introduction": "I am a Data Engineer.",
                },
                request_only=True,
            ),
        ],
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
                        "user_id": {"type": "integer", "example": 2},
                        "status": {"type": "string", "enum": ["W"], "example": "W"},
                        "teacher_id": {"type": "integer", "example": 2},
                    },
                    "required": ["message", "user_id", "status", "teacher_id"],
                    "example": {
                        "message": "Teacher profile submitted successfully. Awaiting approval.",
                        "user_id": 2,
                        "status": "W"
                    },
                },
            ),
        },
    )
    def post(self, request):
        user_id = request.data.get("user.id")

        if not user_id:
            return Response({"detail": "user.id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id, role="T", status="I")
        except User.DoesNotExist:
            return Response({"detail": "Teacher not found or account status is not `Incomplete Profile`."}, status=status.HTTP_404_NOT_FOUND)

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
        user.status = "W"
        user.save()
        
        try:
            credentials_data = process_credential_files_upload(request.FILES, user)
        except ValueError as e:
            return Response({"teacher.credentials": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        teacher_data = {
            "user": user.pk,
            "current_workplace": request.data.get("teacher.current_workplace", "").strip(),
            "teacher_type": request.data.get("teacher.teacher_type"),
            "experience_year": request.data.get("teacher.experience_year"),
            "introduction": request.data.get("teacher.introduction", "").strip(),
            "credentials": credentials_data,
        }

        serializer = self.get_serializer(data=teacher_data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()
        response = {
            "message": "Teacher profile submitted successfully. Awaiting approval.",
            "user_id": user.id,
            "status": user.status
        }

        return Response(response, status=status.HTTP_201_CREATED)
