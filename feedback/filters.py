import django_filters

from .models import TestFeedback


class TestFeedbackFilterSet(django_filters.FilterSet):
    class Meta:
        model = TestFeedback
        fields = ["created_by"]
