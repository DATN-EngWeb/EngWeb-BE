from django.urls import path
from .views import (
    ProductiveTestHistoryListCreateView,
    ProductiveTestHistoryRetrieveView,
)

app_name = "test_histories"

urlpatterns = [
    # List and create productive test histories
    path(
        "productive",
        ProductiveTestHistoryListCreateView.as_view(),
        name="productive_history_list_create",
    ),
    # Retrieve a specific productive test history
    path(
        "productive/<int:history_id>",
        ProductiveTestHistoryRetrieveView.as_view(),
        name="productive_history_retrieve",
    ),
]
