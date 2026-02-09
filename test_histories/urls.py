from django.urls import path
from .views import ProductiveTestHistoryListCreateView

app_name = "test_histories"

urlpatterns = [
    # List and create productive test histories
    path(
        "productive/",
        ProductiveTestHistoryListCreateView.as_view(),
        name="productive_history_list_create",
    ),
]
