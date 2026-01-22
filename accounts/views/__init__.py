# Export all views from submodules
from .authentication import (
    CustomTokenObtainPairView,
    LogoutAPIView,
    GoogleLoginAPIView,
    FacebookLoginAPIView,
)
from .registration import (
    UserRegistrationAPIView,
    VerifyRegistrationOTPAPIView,
    ResendRegistrationOTPAPIView,
    TeacherSubmitProfileAPIView,
)
from .password import (
    ForgotPasswordAPIView,
    ForgotPasswordVerifyOTPAPIView,
    ResetPasswordAPIView,
    ResendForgotPasswordOTPAPIView,
)
from .users import (
    UserListAPIView,
    UserRetrieveUpdateDestroyAPIView,
)

__all__ = [
    # Authentication
    "CustomTokenObtainPairView",
    "LogoutAPIView",
    "GoogleLoginAPIView",
    "FacebookLoginAPIView",
    # Registration
    "UserRegistrationAPIView",
    "VerifyRegistrationOTPAPIView",
    "ResendRegistrationOTPAPIView",
    "TeacherSubmitProfileAPIView",
    # Password
    "ForgotPasswordAPIView",
    "ForgotPasswordVerifyOTPAPIView",
    "ResetPasswordAPIView",
    "ResendForgotPasswordOTPAPIView",
    # Users
    "UserListAPIView",
    "UserRetrieveUpdateDestroyAPIView",
]
