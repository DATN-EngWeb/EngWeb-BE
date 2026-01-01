import django_filters
from .models import Test


class TestFilter(django_filters.FilterSet):
    """
    Filter class for Test model
    Allows filtering by level, skill, and status
    """
    
    level = django_filters.CharFilter(
        field_name='level',
        lookup_expr='exact',
        help_text='Filter by level (A1, A2, B1, B2)'
    )
    
    skill = django_filters.CharFilter(
        field_name='skill',
        lookup_expr='exact',
        help_text='Filter by skill (R, L, S, W)'
    )
    
    status = django_filters.CharFilter(
        field_name='status',
        lookup_expr='exact',
        help_text='Filter by status (D, I, P, R)'
    )
    
    class Meta:
        model = Test
        fields = ['level', 'skill', 'status']
