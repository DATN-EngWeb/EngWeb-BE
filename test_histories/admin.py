from django.contrib import admin

from test_histories.models import (
    ProductiveTestHistory,
    ReceptiveTestHistory,
    ReceptiveAnswerHistory,
)


# Register your models here.
@admin.register(ProductiveTestHistory)
class ProductiveTestHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "productive_test",
        "type",
        "attempt",
        "start_time",
        "end_time",
        "total_time",
        "audio_path",
        "user_answer_text",
        "user_note_text",
        "ai_feedback",
        "earned_bonus_point",
    )
    list_filter = ("type", "start_time")
    search_fields = (
        "student__user__username",
        "student__user__full_name",
        "productive_test__test__title",
    )
    ordering = ("-start_time",)


@admin.register(ReceptiveTestHistory)
class ReceptiveTestHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "receptive_test",
        "type",
        "attempt",
        "start_time",
        "end_time",
        "total_time",
        "total_score",
        "bonus_point",
        "earned_bonus_point",
    )
    list_filter = ("type", "start_time")
    search_fields = (
        "student__user__username",
        "student__user__full_name",
        "receptive_test__test__title",
    )
    ordering = ("-start_time",)


@admin.register(ReceptiveAnswerHistory)
class ReceptiveAnswerHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "receptive_test_history",
        "receptive_question",
        "receptive_answer",
        "user_answer_text",
        "is_correct",
    )
    list_filter = ("is_correct",)
    search_fields = (
        "receptive_test_history__student__user__username",
        "receptive_question__content",
    )