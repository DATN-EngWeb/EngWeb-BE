from django.urls import path
from .views.tests import TestListView, TestCreateView

urlpatterns = [
    path('', TestListView.as_view(), name='test-list'),
    path('create/', TestCreateView.as_view(), name='test-create'),
]
