import django_filters

from .models import UserLevel


class UserLevelFilter(django_filters.FilterSet):
    level_number = django_filters.NumberFilter(
        field_name="level_number",
        help_text="Filter by level number",
    )
    level_title = django_filters.CharFilter(
        field_name="level_title",
        lookup_expr="icontains",
        help_text="Filter by level title (case-insensitive partial match)",
    )

    class Meta:
        model = UserLevel
        fields = ["level_number", "level_title"]
