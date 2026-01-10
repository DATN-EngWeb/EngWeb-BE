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
        summary="List Writing Criteria Templates",
        description=(
            "Get all Writing Criteria Templates with optional filtering by level and band.\n\n"
            "**Filter parameters:**\n"
            "- `level`: Filter by CEFR level (A1, A2, B1, B2)\n"
            "- `band`: Filter by band score (1, 2, 3, ...)\n\n"
            "**Example:**\n"
            "- `/api/tests/writing-criteria?level=B1` - Get all B1 level criteria\n"
            "- `/api/tests/writing-criteria?level=B1&band=3` - Get B1 level, band 3 criteria"
        ),
        tags=["writing-criteria"],
        parameters=[
            OpenApiParameter(
                name="level",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by CEFR level",
                enum=["A1", "A2", "B1", "B2"],
                required=False,
            ),
            OpenApiParameter(
                name="band",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by band score",
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
