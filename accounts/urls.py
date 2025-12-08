from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserRegistrationAPIView,
    VerifyRegistrationOTPAPIView,
    ResendRegistrationOTPAPIView,
    CustomTokenObtainPairView,
    LogoutAPIView,
    TeacherAPIView,
)

urlpatterns = [
    path('register', UserRegistrationAPIView.as_view(), name='user-register'),
    path('verify-otp', VerifyRegistrationOTPAPIView.as_view(), name='verify-otp'),
    path('resend-otp', ResendRegistrationOTPAPIView.as_view(), name='resend-otp'),
    path('teachers', TeacherAPIView.as_view(), name='teacher-profile'),
    path('token', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout', LogoutAPIView.as_view(), name='token-logout'),
]
