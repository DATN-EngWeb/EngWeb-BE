from django.urls import path

from .views.overview_tests import TestOverviewListCreateView
from .views.receptive_tests import ReceptiveTestCreateView
from .views.productive_tests import ProductiveTestCreateView
from .views.writing_criteria import WritingCriteriaTemplateListView
from .views.completed_bonus import CompletedBonusListView
from .views.full_tests import (
    ReceptiveTestRetrieveUpdateDestroyAPIView,
    ProductiveTestRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path("overview", TestOverviewListCreateView.as_view(), name="test"),
    path(
        "receptive/<int:test_id>",
        ReceptiveTestCreateView.as_view(),
        name="receptive-test",
    ),
    path(
        "productive/<int:test_id>",
        ProductiveTestCreateView.as_view(),
        name="productive-test",
    ),
    path(
        "writing-criteria",
        WritingCriteriaTemplateListView.as_view(),
        name="writing-criteria",
    ),
    path(
        "completed-bonus",
        CompletedBonusListView.as_view(),
        name="completed-bonus",
    ),
    path(
        "full-test/receptive/<int:test_id>",
        ReceptiveTestRetrieveUpdateDestroyAPIView.as_view(),
        name="receptive-test-retrieve",
    ),
    path(
        "full-test/productive/<int:test_id>",
        ProductiveTestRetrieveUpdateDestroyAPIView.as_view(),
        name="productive-test-retrieve",
    ),
]
