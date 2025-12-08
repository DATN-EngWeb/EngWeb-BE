from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import User, Student
from .serializers import UserSerializer, StudentSerializer
from .utils import (
    create_otp_code, 
    cache_register_otp, 
    send_registration_otp_email, 
    resend_registration_otp_email,
    verify_registration_otp,
    delete_registration_otp_cache
)

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
