from rest_framework import generics, permissions
import django_filters

from ..models import CompletedBonus
from ..serializers.completed_bonus import CompletedBonusSerializer
from ..filters import CompletedBonusFilter

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
)


class CompletedBonusListView(generics.ListAPIView):
    """
    GET: Lấy danh sách Completed Bonus, lọc theo skill và level
    """

    queryset = CompletedBonus.objects.all().order_by("skill", "level")
    serializer_class = CompletedBonusSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = CompletedBonusFilter

    @extend_schema(
        summary="Lấy danh sách Completed Bonus",
        description=(
            "Lấy tất cả Completed Bonus với bộ lọc theo skill và level.\n\n"
            "**Tham số lọc:**\n"
            "- `skill`: Lọc theo kỹ năng (R: Reading, L: Listening, S: Speaking, W: Writing)\n"
            "- `level`: Lọc theo trình độ CEFR (A1, A2, B1, B2)\n\n"
            "**Ví dụ:**\n"
            "- `/api/tests/completed-bonus?skill=R` - Lấy tất cả bonus của kỹ năng Reading\n"
            "- `/api/tests/completed-bonus?skill=R&level=B1` - Lấy bonus của kỹ năng Reading, level B1"
        ),
        tags=["completed-bonus"],
        parameters=[
            OpenApiParameter(
                name="skill",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo kỹ năng (R: Reading, L: Listening, S: Speaking, W: Writing)",
                enum=["R", "L", "S", "W"],
                required=False,
            ),
            OpenApiParameter(
                name="level",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Lọc theo trình độ CEFR",
                enum=["A1", "A2", "B1", "B2"],
                required=False,
            ),
        ],
        responses={
            200: CompletedBonusSerializer(many=True),
            401: OpenApiResponse(
                description="Authentication required",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
