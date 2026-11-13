from django.urls import path

from apps.accounts import api, views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("api/v1/auth/register/", api.register, name="api_register"),
    path("api/v1/auth/login/", api.login_api, name="api_login"),
    path("api/v1/auth/logout/", api.logout_api, name="api_logout"),
]
