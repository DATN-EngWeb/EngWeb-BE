from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from test_histories.models import (
    ProductiveTestHistory,
    ReceptiveAnswerHistory,
    ReceptiveTestHistory,
)
from test_histories.permissions import IsStudent
from tests.models import ReceptiveQuestion


class StatisticSummaryView(APIView):
    permission_classes = [IsStudent]

    @staticmethod
    def _normalize_skill(skill):
        return (skill or "").strip().upper()

    @staticmethod
    def _to_attempt_item(history, score=None, normalized_score=None):
        attempt_date = history.end_time or history.start_time
        return {
            "history_id": history.id,
            "date": attempt_date.isoformat() if attempt_date else None,
            "score": score,
            "normalized_score": normalized_score,
        }

    @staticmethod
    def _calculate_normalized_score(score, max_score):
        if score is None or not max_score or max_score <= 0:
            return None
        return round((score / max_score) * 100, 2)

    @staticmethod
    def _calculate_receptive_average_score(submitted_histories):
        normalized_scores = []
        for history in submitted_histories:
            max_score = history.receptive_test.total_score
            achieved_score = history.total_score or 0
            if max_score and max_score > 0:
                normalized_scores.append((achieved_score / max_score) * 100)

        if not normalized_scores:
            return 0.0

        return round(sum(normalized_scores) / len(normalized_scores), 2)

    @staticmethod
    def _calculate_receptive_accuracy(submitted_histories):
        if not submitted_histories:
            return 0.0

        receptive_test_ids = {
            history.receptive_test_id for history in submitted_histories
        }
        question_count_rows = (
            ReceptiveQuestion.objects.filter(
                receptive_part__receptive_test_id__in=receptive_test_ids
            )
            .values("receptive_part__receptive_test_id")
            .annotate(total_questions=Count("id"))
        )
        question_count_by_test = {
            row["receptive_part__receptive_test_id"]: row["total_questions"]
            for row in question_count_rows
        }

        history_ids = [history.id for history in submitted_histories]
        correct_count_rows = (
            ReceptiveAnswerHistory.objects.filter(
                receptive_test_history_id__in=history_ids,
                is_correct=True,
            )
            .values("receptive_test_history_id")
            .annotate(total_correct=Count("id"))
        )
        correct_count_by_history = {
            row["receptive_test_history_id"]: row["total_correct"]
            for row in correct_count_rows
        }

        total_questions = 0
        total_correct_answers = 0
        for history in submitted_histories:
            total_questions += question_count_by_test.get(history.receptive_test_id, 0)
            total_correct_answers += correct_count_by_history.get(history.id, 0)

        if total_questions == 0:
            return 0.0

        return round((total_correct_answers / total_questions) * 100, 2)

    @staticmethod
    def _calculate_average_completion_time(submitted_histories):
        durations = [
            history.total_time
            for history in submitted_histories
            if history.total_time is not None
        ]
        if not durations:
            return 0.0

        return round(sum(durations) / len(durations), 2)

    def _build_receptive_summary(self, student, skill):
        submitted_queryset = (
            ReceptiveTestHistory.objects.filter(
                student=student,
                receptive_test__test__skill=skill,
                type="S",
            )
            .select_related("receptive_test")
            .order_by("-end_time", "-start_time")
        )

        last_30_attempt = [
            self._to_attempt_item(
                history,
                history.total_score,
                self._calculate_normalized_score(
                    history.total_score,
                    history.receptive_test.total_score,
                ),
            )
            for history in submitted_queryset[:30]
        ]

        submitted_histories = list(submitted_queryset)
        completed_tests_count = (
            submitted_queryset.values("receptive_test_id").distinct().count()
        )

        average_score = self._calculate_receptive_average_score(submitted_histories)
        accuracy = self._calculate_receptive_accuracy(submitted_histories)
        average_completion_time = self._calculate_average_completion_time(
            submitted_histories
        )

        return {
            "last_30_attempt": last_30_attempt,
            "average_score": average_score,
            "completed_tests_count": completed_tests_count,
            "accuracy": accuracy,
            "average_completion_time": average_completion_time,
        }

    def _build_productive_summary(self, student, skill):
        submitted_queryset = ProductiveTestHistory.objects.filter(
            student=student, productive_test__test__skill=skill, type="S"
        ).order_by("-end_time", "-start_time")

        last_30_attempt = [
            self._to_attempt_item(history, None) for history in submitted_queryset[:30]
        ]

        submitted_histories = list(submitted_queryset)
        completed_tests_count = (
            submitted_queryset.values("productive_test_id").distinct().count()
        )
        average_completion_time = self._calculate_average_completion_time(
            submitted_histories
        )

        return {
            "last_30_attempt": last_30_attempt,
            "completed_tests_count": completed_tests_count,
            "average_completion_time": average_completion_time,
        }

    @extend_schema(
        summary="Thống kê tổng quan theo kỹ năng của học viên",
        description=(
            "Trả về thống kê tổng quan theo 1 kỹ năng (`R`, `L`, `S`, `W`) của học viên đang đăng nhập.\n\n"
            "- `last_30_attempt`: 30 lịch sử làm bài gần nhất\n"
            "- `average_score`: chỉ áp dụng cho `R/L`, quy đổi thang 100\n"
            "- `completed_tests_count`: số test đã hoàn thành (distinct test, chỉ tính submitted)\n"
            "- `accuracy`: chỉ áp dụng cho `R/L`, tính theo tổng số câu đúng / tổng số câu hỏi\n"
            "- `average_completion_time`: thời gian làm bài trung bình (giây), áp dụng cho cả 4 kỹ năng"
        ),
        tags=["statistics"],
        parameters=[
            OpenApiParameter(
                name="skill",
                type=str,
                location=OpenApiParameter.PATH,
                required=True,
                enum=["R", "L", "S", "W"],
                description="Kỹ năng cần lấy thống kê",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Lấy thống kê thành công"),
            400: OpenApiResponse(description="Skill không hợp lệ"),
            401: OpenApiResponse(description="Chưa đăng nhập"),
            403: OpenApiResponse(description="Chỉ student được phép truy cập"),
        },
    )
    def get(self, request, skill):
        normalized_skill = self._normalize_skill(skill)
        if normalized_skill not in {"R", "L", "S", "W"}:
            return Response(
                {"detail": "Invalid skill. Use one of: R, L, S, W."},
                status=400,
            )

        student = request.user.student
        if normalized_skill in {"R", "L"}:
            summary = self._build_receptive_summary(student, normalized_skill)
        elif normalized_skill in {"S", "W"}:
            summary = self._build_productive_summary(student, normalized_skill)
        else:
            return Response(
                {"detail": "Invalid skill. Use one of: R, L, S, W."},
                status=400,
            )

        return Response(
            {
                "skill": normalized_skill,
                **summary,
            }
        )
