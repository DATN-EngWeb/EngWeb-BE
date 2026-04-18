from django_filters import rest_framework as filters


class NotificationFilter(filters.FilterSet):
    """Filter for notifications - currently only supports is_read filter"""
    is_read = filters.BooleanFilter(field_name="is_read")

    class Meta:
        fields = ["is_read"]
