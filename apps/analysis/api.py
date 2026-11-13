"""REST API проверок (задание 14). Регистрация и вход — в apps/accounts/api.py."""
import logging
import time
import unicodedata

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import exception_handler as drf_exception_handler

from apps.analysis.models import Check
from apps.analysis.services import (
    analyze_sms,
    analyze_url,
    check_to_dict,
    filter_checks,
    find_recent_duplicate,
    save_check,
)
from ml.predictor import ModelUnavailable, is_sms_model_ready, is_url_model_ready, load_sms_meta, load_url_meta
from ml.url_features import validate_url

logger = logging.getLogger(__name__)
MAX_SMS_LENGTH = 1000
PAGE_SIZE = 20
_ERROR_CODES = {400: "VALIDATION_ERROR", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 429: "RATE_LIMITED"}
_ERROR_MESSAGES = {
    401: "Требуется вход в систему.",
    403: "Доступ запрещён.",
    404: "Запись не найдена.",
    429: "Слишком много проверок: не более 30 в минуту. Подождите немного.",
}


def _error(http_status: int, code: str, message: str) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=http_status)


def exception_handler(exc, context):
    """Единый формат ошибок API; без входа отвечаем 401, а не 403."""
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return _error(401, _ERROR_CODES[401], _ERROR_MESSAGES[401])
    response = drf_exception_handler(exc, context)
    if response is not None:
        code = _ERROR_CODES.get(response.status_code, "ERROR")
        message = _ERROR_MESSAGES.get(response.status_code, "Некорректный запрос.")
        response.data = {"error": {"code": code, "message": message}}
    return response


class ChecksThrottle(UserRateThrottle):
    scope = "checks"


def _clean_text(value: str) -> str:
    return "".join(
        ch for ch in value if ch in "\n\t" or not unicodedata.category(ch).startswith("C")
    ).strip()


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    return Response(
        {
            "status": "ok",
            "models": {
                "sms": {"loaded": is_sms_model_ready(), "version": load_sms_meta().get("version")},
                "url": {"loaded": is_url_model_ready(), "version": load_url_meta().get("version")},
            },
        }
    )


MODEL_UNAVAILABLE = "Анализ временно недоступен: модель не загружена."


def _run_check(request, check_type: str, value: str, analyze) -> Response:
    started = time.perf_counter()
    duplicate = find_recent_duplicate(request.user, check_type, value)
    if duplicate is not None:
        return Response(check_to_dict(duplicate))
    try:
        result = analyze(value)
    except ModelUnavailable:
        return _error(503, "MODEL_UNAVAILABLE", MODEL_UNAVAILABLE)
    check = save_check(request.user, result, value)
    # Текст SMS в лог не пишется: только id, категория и время (НФТ-9, НФТ-1).
    logger.info("api check id=%s category=%s %.0f ms", check.id, check.category, (time.perf_counter() - started) * 1000)
    return Response(check_to_dict(check))


@api_view(["POST"])
@throttle_classes([ChecksThrottle])
def check_sms(request):
    raw = request.data.get("text") if isinstance(request.data, dict) else None
    if not isinstance(raw, str) or not _clean_text(raw):
        return _error(400, "VALIDATION_ERROR", "Текст SMS не может быть пустым.")
    text = _clean_text(raw)
    if len(text) > MAX_SMS_LENGTH:
        return _error(400, "VALIDATION_ERROR", f"Текст SMS длиннее {MAX_SMS_LENGTH} символов.")
    return _run_check(request, Check.TYPE_SMS, text, analyze_sms)


@api_view(["POST"])
@throttle_classes([ChecksThrottle])
def check_url(request):
    raw = request.data.get("url") if isinstance(request.data, dict) else None
    _, error = validate_url(raw)
    if error:
        return _error(400, "VALIDATION_ERROR", error)
    return _run_check(request, Check.TYPE_URL, raw.strip(), analyze_url)


def _own_checks(request):
    queryset = Check.objects.prefetch_related("url_results", "detected_features")
    return queryset.filter(user=request.user)


@api_view(["GET"])
def checks_list(request):
    paginator = Paginator(filter_checks(_own_checks(request), request.query_params), PAGE_SIZE)
    page = paginator.get_page(request.query_params.get("page"))
    return Response(
        {
            "count": paginator.count,
            "page": page.number,
            "pages": paginator.num_pages,
            "results": [check_to_dict(check) for check in page],
        }
    )


@api_view(["GET", "DELETE"])
def check_detail(request, pk: int):
    check = get_object_or_404(_own_checks(request), pk=pk)
    if request.method == "DELETE":
        check.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(check_to_dict(check))
