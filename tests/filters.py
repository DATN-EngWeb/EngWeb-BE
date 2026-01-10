import django_filters
from .models import Test, WritingCriteriaTemplate


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
        field_name='type',
        choices=TYPE_CHOICES,
        help_text='Filter by type (R: Receptive, P: Productive)'
    )

    level = django_filters.ChoiceFilter(
        field_name='level',
        choices=LEVEL_CHOICES,
        help_text='Filter by level (A1, A2, B1, B2)'
    )

    skill = django_filters.ChoiceFilter(
        field_name='skill',
        choices=SKILL_CHOICES,
        help_text='Filter by skill (R, L, S, W)'
    )

    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=STATUS_CHOICES,
        help_text='Filter by status (D, I, P, R)'
    )

    class Meta:
        model = Test
        fields = ['type', 'level', 'skill', 'status']


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
        field_name='level',
        choices=LEVEL_CHOICES,
        help_text='Filter by level (A1, A2, B1, B2)'
    )

    band = django_filters.NumberFilter(
        field_name='band',
        help_text='Filter by band (1, 2, 3, ...)'
    )

    class Meta:
        model = WritingCriteriaTemplate
        fields = ['level', 'band']
