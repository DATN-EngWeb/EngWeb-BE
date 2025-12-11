from .models import User, Teacher, Student
from django.contrib import admin

# custom display for User in admin panel
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'full_name', 'role', 'status', 'is_active')
                    
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'teacher_type', 'current_workplace', 'experience_year')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'title', 'cumulative_point', 'weekly_point', 'streak_count')
