from django.urls import path

from apps.analysis import views

urlpatterns = [
    path("check/sms/", views.check_sms_page, name="check_sms"),
    path("check/url/", views.check_url_page, name="check_url"),
    path("history/", views.history_page, name="history"),
    path("api/v1/health/", views.health, name="api_health"),
]
