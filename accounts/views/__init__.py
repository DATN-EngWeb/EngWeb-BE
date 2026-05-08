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
from .admin import (
    AdminListUserAPIView,
    AdminRetrieveUpdateDestroyUserAPIView,
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
    "AdminListUserAPIView",
    "AdminRetrieveUpdateDestroyUserAPIView",
]
