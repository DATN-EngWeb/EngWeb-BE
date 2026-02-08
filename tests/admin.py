from django.contrib import admin
from .models import (
    EXPBonusRule,
    Test,
    ReceptiveTest,
    ProductiveTest,
    ReceptivePart,
    ReceptiveQuestion,
    ReceptiveAnswer,
    WritingCriteriaTemplate,
    CompletedBonus,
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
        "status",
        "created_at",
        "created_by",
    )


@admin.register(ReceptiveTest)
class ReceptiveTestAdmin(admin.ModelAdmin):
    list_display = ("test", "total_score")


@admin.register(ProductiveTest)
class ProductiveTestAdmin(admin.ModelAdmin):
    list_display = (
        "test",
        "format",
        "topic",
        "description",
        "min_word",
        "glue_text",
        "glue_resources",
    )


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


@admin.register(WritingCriteriaTemplate)
class WritingCriteriaTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "level",
        "band",
        "content",
        "communicative_achievement",
        "organisation",
        "language",
    )


@admin.register(CompletedBonus)
class CompletedBonusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "skill",
        "level",
        "completed_bonus",
    )


@admin.register(EXPBonusRule)
class EXPBonusRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "min_percentage",
        "max_percentage",
        "exp_percentage",
        "rating",
        "feedback_message",
    )
