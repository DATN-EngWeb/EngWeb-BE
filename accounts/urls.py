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
    ChangePasswordAPIView
)
from .views.admin import (
    AdminOverviewAPIView,
    AdminListUserAPIView,
    AdminRetrieveUpdateDestroyUserAPIView,
)
from .views.teacher import TeacherRetrieveUpdateAPIView
from .views.student import StudentRetrieveUpdateAPIView

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Authentication endpoints
    path("token", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout", LogoutAPIView.as_view(), name="token-logout"),
    path("auth/google/login", GoogleLoginAPIView.as_view(), name="google-login"),
    path("auth/facebook/login", FacebookLoginAPIView.as_view(), name="facebook-login"),

    # Registration endpoints
    path("registration", UserRegistrationAPIView.as_view(), name="registration"),
    path("verify-otp/registration", VerifyRegistrationOTPAPIView.as_view(), name="verify-otp-registration"),
    path("resend-otp/registration", ResendRegistrationOTPAPIView.as_view(), name="resend-otp-registration"),
    path("teachers/submit-profile", TeacherSubmitProfileAPIView.as_view(), name="teacher-submit-profile"),
    
    # Password endpoints
    path("forgot-password", ForgotPasswordAPIView.as_view(), name="forgot-password"),
    path("verify-otp/forgot-password", ForgotPasswordVerifyOTPAPIView.as_view(), name="verify-otp-forgot-password"),
    path("resend-otp/forgot-password", ResendForgotPasswordOTPAPIView.as_view(), name="resend-otp-forgot-password"),
    path("reset-password", ResetPasswordAPIView.as_view(), name="reset-password"),
    path("change-password", ChangePasswordAPIView.as_view(), name="change-password"),

    # Admin manage user endpoints
    path("admin-users", AdminListUserAPIView.as_view(), name="admin-list-user"),
    path("admin-users/overview", AdminOverviewAPIView.as_view(), name="admin-overview"),
    path("admin-users/<int:pk>", AdminRetrieveUpdateDestroyUserAPIView.as_view(), name="admin-retrieve-update-destroy-user"),

    # Teacher endpoints
    path("teachers/<int:pk>", TeacherRetrieveUpdateAPIView.as_view(), name="teacher-retrieve-update"),

    # Student endpoints
    path("students/<int:pk>", StudentRetrieveUpdateAPIView.as_view(), name="student-retrieve-update"),
]
