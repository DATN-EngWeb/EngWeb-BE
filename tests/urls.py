from django.urls import path
from .views.tests import TestListCreateView
from .views.receptive_tests import ReceptiveTestCreateView

urlpatterns = [
    path("", TestListCreateView.as_view(), name="test"),
    path(
        "/receptive/<int:test_id>",
        ReceptiveTestCreateView.as_view(),
        name="receptive-test",
    ),
]
