from django.urls import path

from apps.analysis import api, views

urlpatterns = [
    path("check/sms/", views.check_sms_page, name="check_sms"),
    path("check/url/", views.check_url_page, name="check_url"),
    path("checks/<int:pk>/", views.result_page, name="result"),
    path("checks/<int:pk>/delete/", views.delete_check, name="delete_check"),
    path("history/", views.history_page, name="history"),
    path("history/export/", views.history_export, name="history_export"),
    path("api/v1/health/", api.health, name="api_health"),
    path("api/v1/check/sms/", api.check_sms, name="api_check_sms"),
    path("api/v1/check/url/", api.check_url, name="api_check_url"),
    path("api/v1/checks/", api.checks_list, name="api_checks"),
    path("api/v1/checks/<int:pk>/", api.check_detail, name="api_check_detail"),
]
