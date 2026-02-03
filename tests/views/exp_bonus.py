from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
import django_filters

from ..models import CompletedBonus, EXPBonusRule, Test
from ..serializers.exp_bonus import (
    CompletedBonusSerializer,
    EXPBonusCalculateRequestSerializer,
    EXPBonusCalculateResponseSerializer,
)
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
        tags=["exp-bonus"],
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


class EXPBonusCalculateView(APIView):
    """
    POST: Calculate EXP bonus based on test completion percentage
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Tính EXP bonus sau khi hoàn thành bài test",
        description=(
            "Tính toán EXP bonus dựa trên:\n\n"
            "1. **test_id**: ID của bài test để xác định skill và level\n"
            "2. **completion_percentage**: Phần trăm hoàn thành bài test (0-100)\n\n"
            "**Cách tính:**\n"
            "- Dựa vào `completion_percentage`, tìm `EXPBonusRule` phù hợp (min_percentage <= percentage < max_percentage)\n"
            "- Dựa vào `test_id`, xác định `skill` và `level` của bài test\n"
            "- Tìm `CompletedBonus` tương ứng với skill và level\n"
            "- EXP nhận được = `completed_bonus` × `exp_percentage` / 100"
        ),
        tags=["exp-bonus"],
        request=EXPBonusCalculateRequestSerializer,
        responses={
            200: EXPBonusCalculateResponseSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            404: OpenApiResponse(
                description="Test, EXP Bonus Rule or Completed Bonus not found"
            ),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = EXPBonusCalculateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_id = serializer.validated_data["test_id"]
        completion_percentage = serializer.validated_data["completion_percentage"]

        # 1. Get the test to determine skill and level
        try:
            test = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            return Response(
                {"error": f"Test with id {test_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Find the EXP Bonus Rule matching the completion percentage
        # Using half-open interval [min, max), with special handling for 100%
        try:
            if completion_percentage >= 100:
                # Special case: 100% should match the highest tier (90-100%)
                exp_rule = EXPBonusRule.objects.get(max_percentage=100)
            else:
                exp_rule = EXPBonusRule.objects.get(
                    min_percentage__lte=completion_percentage,
                    max_percentage__gt=completion_percentage,
                )
        except EXPBonusRule.DoesNotExist:
            return Response(
                {
                    "error": f"No EXP Bonus Rule found for completion percentage {completion_percentage}%."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except EXPBonusRule.MultipleObjectsReturned:
            return Response(
                {
                    "error": "Multiple EXP Bonus Rules found. Please check data integrity."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 3. Find the Completed Bonus for the test's skill and level
        try:
            completed_bonus = CompletedBonus.objects.get(
                skill=test.skill, level=test.level
            )
        except CompletedBonus.DoesNotExist:
            return Response(
                {
                    "error": f"No Completed Bonus found for skill={test.skill}, level={test.level}."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 4. Calculate EXP earned
        exp_earned = completed_bonus.completed_bonus * exp_rule.exp_percentage / 100

        # 5. Prepare response
        response_data = {
            "test_id": test.id,
            "test_title": test.title,
            "skill": test.get_skill_display(),
            "level": test.level,
            "completion_percentage": completion_percentage,
            "completed_bonus": completed_bonus.completed_bonus,
            "exp_percentage": exp_rule.exp_percentage,
            "exp_earned": exp_earned,
            "rating": exp_rule.rating,
            "feedback_message": exp_rule.feedback_message,
        }

        response_serializer = EXPBonusCalculateResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)
