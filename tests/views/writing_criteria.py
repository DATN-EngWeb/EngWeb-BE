from rest_framework import generics, permissions
import django_filters

from ..models import WritingCriteriaTemplate
from ..serializers.serializers_writing_criteria import WritingCriteriaTemplateSerializer
from ..filters import WritingCriteriaTemplateFilter

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample,
)


class WritingCriteriaTemplateListView(generics.ListAPIView):
    """
    GET: List all Writing Criteria Templates with filtering by level and band
    """

    queryset = WritingCriteriaTemplate.objects.all().order_by("level", "band")
    serializer_class = WritingCriteriaTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = WritingCriteriaTemplateFilter

    @extend_schema(
        summary="Lấy danh sách Writing Criteria Templates",
        description=(
            "Lấy tất cả Writing Criteria Templates với bộ lọc theo level và band.\n\n"
            "**Tham số lọc:**\n"
            "- `level`: Lọc theo trình độ CEFR (A1, A2, B1, B2)\n"
            "- `band`: Lọc theo điểm band (0, 1, 2, 3, 4, 5)\n\n"
            "**Ví dụ:**\n"
            "- `/api/tests/writing-criteria?level=B1` - Lấy tất cả criteria của level B1\n"
            "- `/api/tests/writing-criteria?level=B1&band=3` - Lấy criteria của level B1, band 3"
        ),
        tags=["writing-criteria-template"],
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
        examples=[
            OpenApiExample(
                "WritingCriteriaTemplate list response",
                value=[
                    {
                        "id": 1,
                        "level": "B1",
                        "band": 1,
                        "content": "Content is irrelevant...",
                        "communicative_achievement": "Communicative achievement is not evident...",
                        "organisation": "Organisation is not evident...",
                        "language": "Language is not evident...",
                    },
                    {
                        "id": 2,
                        "level": "B1",
                        "band": 2,
                        "content": "Content is slightly relevant...",
                        "communicative_achievement": "Uses the conventions of the communicative task with limited success...",
                        "organisation": "Text is connected using basic linking words...",
                        "language": "Uses everyday vocabulary generally appropriately...",
                    },
                ],
                response_only=True,
            ),
        ],
        responses={
            200: WritingCriteriaTemplateSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication required",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
