from django_filters import rest_framework as filters
from .models import ProductiveTestHistory


class ProductiveTestHistoryFilter(filters.FilterSet):
    """FilterSet for ProductiveTestHistory"""

    productive_test = filters.NumberFilter(
        field_name="productive_test",
        help_text="Lọc theo ID của Productive Test",
    )

    class Meta:
        model = ProductiveTestHistory
        fields = ["productive_test"]
