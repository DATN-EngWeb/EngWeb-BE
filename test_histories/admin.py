from django.contrib import admin

from test_histories.models import ProductiveTestHistory

# Register your models here.
@admin.register(ProductiveTestHistory)
class ProductiveTestHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "productive_test",
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