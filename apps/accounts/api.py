"""API учётных записей (задание 14): регистрация, вход и выход по сессии."""
from django.contrib.auth import logout
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.forms import RegisterForm
from apps.accounts.views import LOCKOUT_MESSAGE, create_user, try_login


def _user_payload(user) -> dict:
    return {"id": user.id, "username": user.username, "email": user.email}


def _form_error(form) -> Response:
    fields = {name: [str(e) for e in errors] for name, errors in form.errors.items()}
    first = next(iter(fields.values()))[0]
    return Response(
        {"error": {"code": "VALIDATION_ERROR", "message": first, "fields": fields}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _csrf_error(request) -> Response | None:
    """DRF отключает CSRF для анонимных запросов, поэтому вход и регистрация проверяют токен явно."""
    check = CsrfViewMiddleware(lambda req: None)
    check.process_request(request)
    if check.process_view(request, None, (), {}) is None:
        return None
    return Response(
        {"error": {"code": "FORBIDDEN", "message": "Нет CSRF-токена. Обновите страницу и повторите."}},
        status=status.HTTP_403_FORBIDDEN,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    if (error := _csrf_error(request._request)) is not None:
        return error
    data = request.data if isinstance(request.data, dict) else {}
    form = RegisterForm(
        {
            "username": data.get("username", ""),
            "email": data.get("email", ""),
            "password": data.get("password", ""),
            "password2": data.get("password2", data.get("password", "")),
        }
    )
    if not form.is_valid():
        return _form_error(form)
    user = create_user(form)
    return Response(_user_payload(user), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_api(request):
    if (error := _csrf_error(request._request)) is not None:
        return error
    data = request.data if isinstance(request.data, dict) else {}
    username, password = str(data.get("username", "")).strip(), str(data.get("password", ""))
    ok, error = try_login(request._request, username, password)
    if not ok:
        http_status = status.HTTP_429_TOO_MANY_REQUESTS if error == LOCKOUT_MESSAGE else status.HTTP_401_UNAUTHORIZED
        code = "RATE_LIMITED" if http_status == 429 else "UNAUTHORIZED"
        return Response({"error": {"code": code, "message": error}}, status=http_status)
    return Response(_user_payload(request._request.user))


@api_view(["POST"])
def logout_api(request):
    logout(request._request)
    return Response(status=status.HTTP_204_NO_CONTENT)
