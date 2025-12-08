from django.urls import path
from .views import (
    UserRegistrationAPIView,
    VerifyRegistrationOTPAPIView,
    ResendRegistrationOTPAPIView,
)

urlpatterns = [
    path('register', UserRegistrationAPIView.as_view(), name='user-register'),
    path('verify-otp', VerifyRegistrationOTPAPIView.as_view(), name='verify-otp'),
    path('resend-otp', ResendRegistrationOTPAPIView.as_view(), name='resend-otp'),
]
