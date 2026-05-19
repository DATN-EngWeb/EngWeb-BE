from django.urls import path

from .views import StatisticSummaryView, TeacherStatisticSummaryView

app_name = "statistic"

urlpatterns = [
    path(
        "teacher-summary",
        TeacherStatisticSummaryView.as_view(),
        name="teacher-statistic-summary",
    ),
    path(
        "summary/<str:skill>/<str:level>",
        StatisticSummaryView.as_view(),
        name="statistic-summary",
    ),
]
