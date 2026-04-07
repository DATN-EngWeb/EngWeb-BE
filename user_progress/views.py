import django_filters
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics

from .filters import UserLevelFilter
from .models import UserLevel
from .serializers import UserLevelSerializer


class UserLevelListAPIView(generics.ListAPIView):
    queryset = UserLevel.objects.all().order_by("min_xp")
    serializer_class = UserLevelSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = UserLevelFilter

    @extend_schema(
        summary="Danh sách level của người dùng",
        description=(
            "Lấy danh sách level của người dùng, sắp xếp theo `min_xp` tăng dần. "
            "Hỗ trợ lọc theo `level_number` và `level_title`."
        ),
        tags=["user-progress"],
        parameters=[
            OpenApiParameter(
                name="level_number",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Lọc theo số level chính xác",
            ),
            OpenApiParameter(
                name="level_title",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Lọc theo tên level (không phân biệt hoa thường, tìm gần đúng)",
            ),
        ],
        responses={
            200: UserLevelSerializer(many=True),
            401: OpenApiResponse(description="Cần đăng nhập"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserLevelRetrieveAPIView(generics.RetrieveAPIView):
    queryset = UserLevel.objects.all()
    serializer_class = UserLevelSerializer
    lookup_field = "level_number"
    lookup_url_kwarg = "level_number"

    @extend_schema(
        summary="Lấy chi tiết một level",
        description="Lấy thông tin chi tiết của một level cụ thể theo số level.",
        tags=["user-progress"],
        parameters=[
            OpenApiParameter(
                name="level_number",
                type=int,
                location=OpenApiParameter.PATH,
                required=True,
                description="Số level cần lấy",
            ),
        ],
        responses={
            200: UserLevelSerializer,
            401: OpenApiResponse(description="Cần đăng nhập"),
            404: OpenApiResponse(description="Không tìm thấy level"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
