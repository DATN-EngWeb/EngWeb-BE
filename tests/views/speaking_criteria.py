from rest_framework import generics, permissions
import django_filters

from ..models import SpeakingCriteriaTemplate
from ..serializers.speaking_criteria import SpeakingCriteriaTemplateSerializer
from ..filters import SpeakingCriteriaTemplateFilter

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
)


class SpeakingCriteriaTemplateListView(generics.ListAPIView):
    """
    GET: List all Speaking Criteria Templates with filtering by level and band
    """

    queryset = SpeakingCriteriaTemplate.objects.all().order_by("level", "band")
    serializer_class = SpeakingCriteriaTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = SpeakingCriteriaTemplateFilter

    @extend_schema(
        summary="Lấy danh sách Speaking Criteria Templates",
        description=(
            "Lấy tất cả Speaking Criteria Templates với bộ lọc theo level và band.\n\n"
            "**Tham số lọc:**\n"
            "- `level`: Lọc theo trình độ CEFR (A1, A2, B1, B2)\n"
            "- `band`: Lọc theo điểm band (1, 2, 3, 4, 5)\n\n"
            "**Ví dụ:**\n"
            "- `/api/tests/speaking-criteria?level=B1` - Lấy tất cả criteria của level B1\n"
            "- `/api/tests/speaking-criteria?level=B1&band=3` - Lấy criteria của level B1, band 3"
        ),
        tags=["speaking-criteria-template"],
        parameters=[
            OpenApiParameter(
                name="level",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo trình độ CEFR",
                enum=["A1", "A2", "B1", "B2"],
                required=False,
            ),
            OpenApiParameter(
                name="band",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Lọc theo điểm band",
                required=False,
            ),
        ],
        responses={
            200: SpeakingCriteriaTemplateSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication required",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)