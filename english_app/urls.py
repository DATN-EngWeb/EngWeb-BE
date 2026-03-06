from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # accounts API
    path("api/accounts/", include("accounts.urls")),
    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # ReDoc
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Tests API
    path("api/tests/", include("tests.urls")),
    # Storage API
    path("api/storage/", include("storage.urls")),
    # Test Histories API
    path("api/test-histories/", include("test_histories.urls")),
    # Forums API
    path("api/forums/", include("forum.urls")),
    # Feedback API
    path("api/feedback/", include("feedback.urls")),
]
