from django_filters import rest_framework as filters
from .models import ProductiveTestHistory, ReceptiveTestHistory


class ProductiveTestHistoryFilter(filters.FilterSet):
    """FilterSet for ProductiveTestHistory"""

    productive_test = filters.NumberFilter(
        field_name="productive_test",
        help_text="Lọc theo ID của Productive Test",
    )
    type = filters.ChoiceFilter(
        field_name="type",
        choices=[("D", "Draft"), ("S", "Submission")],
        help_text="Lọc theo loại (D=Draft, S=Submission)",
    )
    skill = filters.ChoiceFilter(
        field_name="productive_test__test__skill",
        choices=[("S", "Speaking"), ("W", "Writing")],
        help_text="Lọc theo kỹ năng: S (Speaking) hoặc W (Writing)",
    )
    level = filters.ChoiceFilter(
        field_name="productive_test__test__level",
        choices=[("A1", "A1"), ("A2", "A2"), ("B1", "B1"), ("B2", "B2")],
        help_text="Lọc theo level: A1, A2, B1, B2",
    )

    class Meta:
        model = ProductiveTestHistory
        fields = ["productive_test", "type", "skill", "level"]


class ReceptiveTestHistoryFilter(filters.FilterSet):
    """FilterSet for ReceptiveTestHistory"""

    receptive_test = filters.NumberFilter(
        field_name="receptive_test",
        help_text="Lọc theo ID của Receptive Test",
    )
    type = filters.ChoiceFilter(
        field_name="type",
        choices=[("D", "Draft"), ("S", "Submission")],
        help_text="Lọc theo loại (D=Draft, S=Submission)",
    )
    skill = filters.ChoiceFilter(
        field_name="receptive_test__test__skill",
        choices=[("R", "Reading"), ("L", "Listening")],
        help_text="Lọc theo kỹ năng: R (Reading) hoặc L (Listening)",
    )
    level = filters.ChoiceFilter(
        field_name="receptive_test__test__level",
        choices=[("A1", "A1"), ("A2", "A2"), ("B1", "B1"), ("B2", "B2")],
        help_text="Lọc theo level: A1, A2, B1, B2",
    )

    class Meta:
        model = ReceptiveTestHistory
        fields = ["receptive_test", "type", "skill", "level"]
