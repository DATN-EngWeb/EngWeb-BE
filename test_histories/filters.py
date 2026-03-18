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

    class Meta:
        model = ProductiveTestHistory
        fields = ["productive_test", "type", "skill"]


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

    class Meta:
        model = ReceptiveTestHistory
        fields = ["receptive_test", "type", "skill"]
