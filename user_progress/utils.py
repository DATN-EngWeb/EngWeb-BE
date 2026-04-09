from accounts.models import Student
from user_progress.models import UserLevel


def _serialize_level(level):
    if level is None:
        return None

    return {
        "id": level.id,
        "level_number": level.level_number,
        "level_title": level.level_title,
        "level_icon": level.level_icon,
        "min_xp": level.min_xp,
        "max_xp": level.max_xp,
    }


def sync_student_level_from_cumulative_point(student_id):
    """Synchronize student's level based on current cumulative_point."""
    student = Student.objects.select_for_update().select_related("level").get(
        pk=student_id
    )
    previous_level = student.level
    xp = student.cumulative_point

    target_level = (
        UserLevel.objects.filter(min_xp__lte=xp, max_xp__gte=xp)
        .order_by("-level_number")
        .first()
    )

    # Fallback to highest level whose min_xp is not greater than current XP.
    if target_level is None:
        target_level = (
            UserLevel.objects.filter(min_xp__lte=xp).order_by("-level_number").first()
        )

    # Last fallback to the lowest configured level.
    if target_level is None:
        target_level = UserLevel.objects.order_by("level_number").first()

    if target_level and student.level_id != target_level.id:
        student.level = target_level
        student.save(update_fields=["level"])
        return {
            "leveled_up": True,
            "current_exp": student.cumulative_point,
            "previous_level": _serialize_level(previous_level),
            "current_level": _serialize_level(target_level),
        }

    current_level = target_level or previous_level
    return {
        "leveled_up": False,
        "current_exp": student.cumulative_point,
        "previous_level": _serialize_level(previous_level),
        "current_level": _serialize_level(current_level),
    }
