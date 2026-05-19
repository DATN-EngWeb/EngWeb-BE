import django_filters
from .models import Test, WritingCriteriaTemplate, SpeakingCriteriaTemplate


class TestFilter(django_filters.FilterSet):
    """
    Filter class for Test model
    Allows filtering by type, level, skill, and status
    """

    TYPE_CHOICES = [
        ("R", "Receptive"),
        ("P", "Productive"),
    ]

    LEVEL_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
    ]

    SKILL_CHOICES = [
        ("R", "Reading"),
        ("L", "Listening"),
        ("S", "Speaking"),
        ("W", "Writing"),
    ]

    STATUS_CHOICES = [
        ("D", "Draft"),
        ("I", "In Review"),
        ("P", "Published"),
        ("R", "Removed"),
    ]

    type = django_filters.ChoiceFilter(
        field_name="type",
        choices=TYPE_CHOICES,
        help_text="Filter by type (R: Receptive, P: Productive)",
    )

    level = django_filters.MultipleChoiceFilter(
        field_name="level",
        choices=LEVEL_CHOICES,
        help_text="Filter by multiple levels (A1, A2, B1, B2). Use ?level=A1&level=A2 or ?level=A1,A2",
    )

    skill = django_filters.ChoiceFilter(
        field_name="skill",
        choices=SKILL_CHOICES,
        help_text="Filter by skill (R, L, S, W)",
    )

    status = django_filters.ChoiceFilter(
        field_name="status",
        choices=STATUS_CHOICES,
        help_text="Filter by status (D, I, P, R)",
    )

    year = django_filters.NumberFilter(
        field_name="created_at__year",
        help_text="Filter by year created (e.g., 2024, 2025, 2026)",
    )

    teacher_name = django_filters.CharFilter(
        field_name="created_by__user__full_name",
        lookup_expr="icontains",
        help_text="Filter by teacher's full name (case-insensitive partial match)",
    )

    title = django_filters.CharFilter(
        field_name="title",
        lookup_expr="icontains",
        help_text="Filter by test name (case-insensitive partial match)",
    )

    class Meta:
        model = Test
        fields = ["type", "level", "skill", "status", "year", "teacher_name", "title"]


class WritingCriteriaTemplateFilter(django_filters.FilterSet):
    """
    Filter class for WritingCriteriaTemplate model
    Allows filtering by level and band
    """

    LEVEL_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
    ]

    level = django_filters.ChoiceFilter(
        field_name="level",
        choices=LEVEL_CHOICES,
        help_text="Filter by level (A1, A2, B1, B2)",
    )

    band = django_filters.NumberFilter(
        field_name="band", help_text="Filter by band (1, 2, 3, ...)"
    )

    class Meta:
        model = WritingCriteriaTemplate
        fields = ["level", "band"]


class SpeakingCriteriaTemplateFilter(django_filters.FilterSet):
    """
    Filter class for SpeakingCriteriaTemplate model
    Allows filtering by level and band
    """

    LEVEL_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
    ]

    level = django_filters.ChoiceFilter(
        field_name="level",
        choices=LEVEL_CHOICES,
        help_text="Filter by level (A1, A2, B1, B2)",
    )

    band = django_filters.NumberFilter(
        field_name="band", help_text="Filter by band (1, 2, 3, ...)"
    )

    class Meta:
        model = SpeakingCriteriaTemplate
        fields = ["level", "band"]
