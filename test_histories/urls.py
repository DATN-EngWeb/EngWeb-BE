from django.urls import path
from .views import (
    ProductiveTestHistoryListCreateView,
    ProductiveTestHistoryRetrieveView,
    ReceptiveTestHistoryListCreateView,
    ReceptiveTestHistoryRetrieveView,
)

app_name = "test_histories"

urlpatterns = [
    # Productive test histories
    path(
        "productive",
        ProductiveTestHistoryListCreateView.as_view(),
        name="productive_history_list_create",
    ),
    path(
        "productive/<int:history_id>",
        ProductiveTestHistoryRetrieveView.as_view(),
        name="productive_history_retrieve",
    ),
    
    # Receptive test histories
    path(
        "receptive",
        ReceptiveTestHistoryListCreateView.as_view(),
        name="receptive_history_list_create",
    ),
    path(
        "receptive/<int:history_id>",
        ReceptiveTestHistoryRetrieveView.as_view(),
        name="receptive_history_retrieve",
    ),
]
