from django.contrib import admin
from .models import UserLevel

@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
	list_display = ["level_number", "level_title", "min_xp", "max_xp"]
	search_fields = ["level_title"]
	ordering = ["level_number"]
