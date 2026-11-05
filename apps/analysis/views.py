from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.analysis.models import Check
from apps.analysis.services import check_to_dict, filter_checks
from ml.predictor import is_sms_model_ready

PAGE_SIZE = 20
FILTER_NAMES = ("date_from", "date_to", "type", "category", "risk_level")


@login_required
def check_sms_page(request):
    return render(
        request,
        "analysis/check_sms.html",
        {"active": "sms", "model_ready": is_sms_model_ready()},
    )


@login_required
def check_url_page(request):
    return render(request, "analysis/check_url.html", {"active": "url"})


@login_required
def result_page(request, pk: int):
    check = get_object_or_404(Check.objects.filter(user=request.user), pk=pk)
    return render(
        request,
        "analysis/result.html",
        {"active": "history", "check": check, "payload": check_to_dict(check)},
    )


@login_required
@require_POST
def delete_check(request, pk: int):
    get_object_or_404(Check.objects.filter(user=request.user), pk=pk).delete()
    return redirect("history")


@login_required
def history_page(request):
    queryset = filter_checks(Check.objects.filter(user=request.user), request.GET)
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    filters = {name: request.GET.get(name, "") for name in FILTER_NAMES}
    active_filters = {name: value for name, value in filters.items() if value}
    return render(
        request,
        "analysis/history.html",
        {
            "active": "history",
            "page": page,
            "filters": filters,
            "querystring": urlencode(active_filters),
        },
    )
