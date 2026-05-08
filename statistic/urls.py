from django.urls import path

from .views import StatisticSummaryView

app_name = "statistic"

urlpatterns = [
    path(
        "summary/<str:skill>/<str:level>",
        StatisticSummaryView.as_view(),
        name="statistic-summary",
    ),
]
