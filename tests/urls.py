from django.urls import path
from .views.tests import TestListView, TestCreateView
from .views.receptive_tests import ReceptiveTestView

urlpatterns = [
    path('', TestListView.as_view(), name='test-list'),
    path('create/', TestCreateView.as_view(), name='test-create'),
    path('receptive/<int:test_id>', ReceptiveTestView.as_view(), name='receptive-test'),
]
