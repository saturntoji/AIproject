from django.urls import path

from apps.dashboard import views

urlpatterns = [
    path("", views.dashboard_page, name="dashboard"),
    path("stats/", views.stats_page, name="stats"),
    path("api/v1/stats/summary/", views.stats_summary, name="api_stats_summary"),
]
