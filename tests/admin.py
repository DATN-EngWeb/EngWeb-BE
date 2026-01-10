from django.contrib import admin
from .models import (
    Test,
    ReceptiveTest,
    ProductiveTest,
    ReceptivePart,
    ReceptiveQuestion,
    ReceptiveAnswer,
)


# Register your models here.
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "level",
        "skill",
        "time",
        "description",
        "completed_bonus",
        "status",
        "created_at",
        "created_by",
    )


@admin.register(ReceptiveTest)
class ReceptiveTestAdmin(admin.ModelAdmin):
    list_display = ("test", "total_score", "base_qualified_bonus")


@admin.register(ProductiveTest)
class ProductiveTestAdmin(admin.ModelAdmin):
    list_display = ("test", "format", "question_text", "resources", "criteria")


@admin.register(ReceptivePart)
class ReceptivePartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "receptive_test",
        "order",
        "format",
        "description",
        "content",
        "score",
        "resources",
    )


@admin.register(ReceptiveQuestion)
class ReceptiveQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "receptive_part",
        "question_number",
        "content",
        "explanation",
        "score",
        "resources",
    )


@admin.register(ReceptiveAnswer)
class ReceptiveAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "receptive_question",
        "option_label",
        "answer_text",
        "is_correct",
        "resources",
    )
