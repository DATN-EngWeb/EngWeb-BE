from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import jwt
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import User, Student
from .serializers import (
    UserSerializer,
    StudentSerializer,
    TeacherSerializer,
    CustomTokenObtainPairSerializer,
)
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
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class LogoutAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({"detail": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class UserRegistrationAPIView(generics.GenericAPIView):
    """Create User model and send OTP email. Status is set to 'P' (Pending Verification)"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        role = request.data.get('role', '').upper()
        
        # Validate role
        if role not in ['S', 'T']:
            return Response(
                {"detail": "Invalid role. Must be 'S' (Student) or 'T' (Teacher)."},
                status=status.HTTP_400_BAD_REQUEST
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
        role_name = 'Student' if role == 'S' else 'Teacher'
        response = {
            "message": f"{role_name} account registered successfully. Please check your email to verify your account.",
            "user_id": user.id
        }
        
        return Response(response, status=status.HTTP_201_CREATED)

class VerifyRegistrationOTPAPIView(generics.GenericAPIView):
    """Verify OTP code for registration. Updates user status: 
        + Student: P → V (Verified)
        + Teacher: P → I (Incomplete Profile)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        otp_code = request.data.get('otp_code')
        
        # Verify OTP
        try:
            cache_data = verify_registration_otp(user_id, otp_code)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user and verify status is Pending
        try:
            user = User.objects.get(id=user_id, status='P')
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found or already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status based on role
        if user.role == 'S':
            user.status = 'V'
        elif user.role == 'T':
            user.status = 'I'
        else:
            return Response(
                {"detail": "Invalid user role."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.save()
        
        # Delete OTP from cache
        delete_registration_otp_cache(user_id)
        
        # Response message based on role
        role_name = 'Student' if user.role == 'S' else 'Teacher'
        
        # Create Student record if role is Student. Teacher record will be created later when they submit profile
        if user.role == 'S':
            student_serializer = StudentSerializer(data={}, context={'user': user})
            student_serializer.is_valid()
            student_serializer.save()
        
        response = {
            "message": f"{role_name} account verified successfully.",
            "user_id": user.id,
            "status": user.status
        }
        
        return Response(response, status=status.HTTP_200_OK)

class ResendRegistrationOTPAPIView(generics.GenericAPIView):
    """Resend OTP code for registration"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        
        # Validate input
        if not user_id:
            return Response(
                {"detail": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Resend OTP
        try:
            resend_registration_otp_email(user_id)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {"message": "OTP code has been resent to your email."},
            status=status.HTTP_200_OK
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

    def post(self, request):
        # Get user_id from form data
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"detail": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "user_id must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get and validate user
        try:
            user = User.objects.get(id=user_id, role='T')
        except User.DoesNotExist:
            return Response(
                {"detail": "Teacher not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only allow when status is Incomplete profile
        if user.status != 'I':
            return Response(
                {"detail": "Profile already completed or not allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and update User fields directly
        user_errors = {}
        full_name = request.data.get('user.full_name', '').strip()
        date_of_birth = request.data.get('user.date_of_birth')
        avatar_file = request.FILES.get('user.avatar')

        if not full_name:
            user_errors['full_name'] = 'This field is required.'
        if not date_of_birth:
            user_errors['date_of_birth'] = 'This field is required.'
        if not avatar_file:
            user_errors['avatar'] = 'This field is required.'

        if user_errors:
            return Response(
                {'user': user_errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update User fields
        user.full_name = full_name
        user.date_of_birth = date_of_birth
        if avatar_file:
            user.avatar = avatar_file

        # Process credential files
        credentials_data = process_credential_files(request.FILES, user_id)
        
        # Validate at least one certificate is required
        if not credentials_data.get('certificates') or len(credentials_data.get('certificates', [])) == 0:
            return Response(
                {'credentials': 'At least one certificate is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare data for serializer (only Teacher fields, no nested user)
        serializer_data = {
            'current_workplace': request.data.get('current_workplace', '').strip(),
            'teacher_type': request.data.get('teacher_type'),
            'experience_year': request.data.get('experience_year'),
            'introduction': request.data.get('introduction', '').strip(),
            'credentials': credentials_data,
        }

        serializer = self.get_serializer(data=serializer_data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        
        # Save user first, then create teacher
        user.status = 'W'  # move to waiting approval after profile completion
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

    def post(self, request):
        username_or_email = request.data.get('username_or_email')

        if not username_or_email:
            return Response(
                {"detail": "Username or email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user by username or email
        try:
            user = User.objects.get(Q(username=username_or_email) | Q(email=username_or_email))
        except User.DoesNotExist:
            return Response(
                {"detail": "Account not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check is_active
        if not user.is_active:
            return Response(
                {"detail": "Account is deactivated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check status - only verified accounts can reset password
        status_code = getattr(user, 'status', None)

        if status_code == 'P':
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
                status=status.HTTP_400_BAD_REQUEST
            )

        if status_code == 'I':
            return Response(
                {
                    "detail": "Please complete your profile first before resetting password.",
                    "status": status_code,
                    "user_id": user.id,
                    "require_certificate": True,
                    "redirect_to": f"/upload-profile?user_id={user.id}",
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if status_code == 'W':
            return Response(
                {
                    "detail": "Account is pending approval. Please wait for admin review.",
                    "status": status_code,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if status_code == 'D':
            return Response(
                {
                    "detail": "Account has been disabled.",
                    "status": status_code,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only status 'V' (Verified) can proceed
        if status_code != 'V':
            return Response(
                {"detail": "Account status does not allow password reset."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate OTP code
        otp_code = create_otp_code()

        # Cache OTP
        cache_forgot_password_otp(user.username, otp_code)

        # Send OTP email
        send_forgot_password_otp_email(user.username, user.email, otp_code)

        response = {
            "message": "OTP code has been sent to your email.",
            "username": user.username
        }

        return Response(response, status=status.HTTP_200_OK)

class ForgotPasswordVerifyOTPAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        otp_code = request.data.get('otp_code')

        if not username or not otp_code:
            return Response(
                {"detail": "Username and OTP code are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get OTP from cache
        cache_key = f"forgot_password_{username}"
        cache_data = cache.get(cache_key)

        if not cache_data:
            return Response(
                {"detail": "OTP code has expired or is invalid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_data = json.loads(cache_data)

        # Verify OTP
        if cache_data['otp_code'] != otp_code:
            return Response(
                {"detail": "Invalid OTP code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP verified, delete cache
        cache.delete(cache_key)

        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate reset token (JWT RefreshToken)
        reset_token = RefreshToken.for_user(user)
        
        # Mark token as password reset token
        reset_token['token_type'] = 'password_reset'
        
        # Set expiry time (30 minutes)
        expiry_time = datetime.now() + timedelta(minutes=30)

        response = {
            "message": "OTP verified successfully.",
            "reset_token": str(reset_token),
            "expires_at": expiry_time.isoformat()
        }

        return Response(response, status=status.HTTP_200_OK)

class ResetPasswordAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')

        if not reset_token or not new_password:
            return Response(
                {"detail": "Reset token and new password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Decode and verify token
            decoded_token = jwt.decode(
                reset_token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_signature": True}
            )

            # Check token type
            if decoded_token.get('token_type') != 'password_reset':
                return Response(
                    {"detail": "Invalid token type for password reset."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get user_id from token
            user_id = decoded_token.get('user_id')

            # Find user
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": "User not found."},
                    status=status.HTTP_400_BAD_REQUEST
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
                {"message": "Password reset successfully. Please login with your new password."},
                status=status.HTTP_200_OK
            )

        except (TokenError, jwt.PyJWTError) as e:
            return Response(
                {"detail": f"Invalid or expired token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Error resetting password: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResendForgotPasswordOTPAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')

        if not username:
            return Response(
                {"detail": "Username is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            resend_forgot_password_otp_email(username)
            return Response(
                {"detail": "OTP code has been resent to your email."},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )