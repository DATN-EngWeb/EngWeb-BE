from django.contrib import admin
from .models import UserLevel, CompletedBonus, EXPBonusRule

@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
	list_display = ["level_number", "level_title", "min_xp", "max_xp"]
	search_fields = ["level_title"]
	ordering = ["level_number"]


@admin.register(CompletedBonus)
class CompletedBonusAdmin(admin.ModelAdmin):
	list_display = ("id", "skill", "level", "completed_bonus")


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
