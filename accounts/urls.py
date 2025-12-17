from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views.authentication import (
    CustomTokenObtainPairView,
    LogoutAPIView,
    GoogleLoginAPIView,
    FacebookLoginAPIView,
)
from .views.registration import (
    UserRegistrationAPIView,
    VerifyRegistrationOTPAPIView,
    ResendRegistrationOTPAPIView,
    TeacherSubmitProfileAPIView,
)
from .views.password import (
    ForgotPasswordAPIView,
    ForgotPasswordVerifyOTPAPIView,
    ResetPasswordAPIView,
    ResendForgotPasswordOTPAPIView,
)
from .views.users import (
    UserListAPIView,
    UserRetrieveUpdateDestroyAPIView,
)
urlpatterns = [
    # Authentication endpoints
    path('token', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout', LogoutAPIView.as_view(), name='token-logout'),
    path('auth/google/login', GoogleLoginAPIView.as_view(), name='google-login'),
    path('auth/facebook/login', FacebookLoginAPIView.as_view(), name='facebook-login'),

    # Registration endpoints
    path('registration', UserRegistrationAPIView.as_view(), name='registration'),
    path('verify-otp/registration', VerifyRegistrationOTPAPIView.as_view(), name='verify-otp-registration'),
    path('resend-otp/registration', ResendRegistrationOTPAPIView.as_view(), name='resend-otp-registration'),
    path('teachers/submit-profile', TeacherSubmitProfileAPIView.as_view(), name='teacher-submit-profile'),

    # Password endpoints
    path('forgot-password', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('verify-otp/forgot-password', ForgotPasswordVerifyOTPAPIView.as_view(), name='verify-otp-forgot-password'),
    path('resend-otp/forgot-password', ResendForgotPasswordOTPAPIView.as_view(), name='resend-otp-forgot-password'),
    path('reset-password', ResetPasswordAPIView.as_view(), name='reset-password'),

    # Users endpoints
    path('users', UserListAPIView.as_view(), name='user-list'),
    path('users/<int:pk>', UserRetrieveUpdateDestroyAPIView.as_view(), name='user-retrieve-update-destroy'),
]
