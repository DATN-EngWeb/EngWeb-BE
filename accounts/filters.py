from django_filters import rest_framework as filters
from django.db.models import Q
from .models import User


class AdminUserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(
        choices=[('S', 'Student'), ('T', 'Teacher'), ('A', 'Admin')]
    )
    status = filters.ChoiceFilter(
        choices=[
            ('P', 'Pending Verification'),
            ('I', 'Incomplete Profile'),
            ('W', 'Waiting Approval'),
            ('V', 'Verified'),
            ('D', 'Disabled'),
        ]
    )
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = User
        fields = ['role', 'status', 'search']

    def filter_search(self, queryset, name, value):
        """
        Search by username or email (case-insensitive)
        """
        if value:
            return queryset.filter(
                Q(username__icontains=value) | Q(email__icontains=value)
            )
        return queryset