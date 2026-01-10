from django.urls import path

from .views.overview_tests import TestOverviewListCreateView
from .views.receptive_tests import ReceptiveTestCreateView
from .views.productive_tests import ProductiveTestCreateView

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
]
