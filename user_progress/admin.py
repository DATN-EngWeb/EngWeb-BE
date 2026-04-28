from django.contrib import admin
from .models import UserLevel, CompletedBonus, EXPBonusRule, StreakRewardRule

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


@admin.register(StreakRewardRule)
class StreakRewardRuleAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"streak_day",
		"xp_reward",
		"ai_turn_reward",
	)
	ordering = ("streak_day",)
	search_fields = ("streak_day",)
