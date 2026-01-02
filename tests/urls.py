from django.urls import path
from .views.tests import TestListView, TestCreateView
from .views.reading_tests import ReadingTestCreateView

urlpatterns = [
    path('', TestListView.as_view(), name='test-list'),
    path('create/', TestCreateView.as_view(), name='test-create'),
    path('reading/<int:test_id>/', ReadingTestCreateView.as_view(), name='reading-test-create'),
]
