from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.analysis.models import Check, DetectedFeature
from apps.analysis.services import check_fragment

ALLOWED_PERIODS = (7, 30, 90)
DEFAULT_PERIOD = 30
RECENT_LIMIT = 10
TOP_FEATURES = 5


@login_required
def dashboard_page(request):
    return render(request, "dashboard/dashboard.html", {"active": "dashboard"})


@login_required
def stats_page(request):
    return render(request, "dashboard/stats.html", {"active": "stats"})


def _parse_period(raw) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PERIOD
    return days if days in ALLOWED_PERIODS else DEFAULT_PERIOD


@api_view(["GET"])
def stats_summary(request):
    """Агрегаты для Dashboard: считаются в БД. Администратору — по всей системе."""
    days = _parse_period(request.query_params.get("days"))
    start_day = timezone.localdate() - timedelta(days=days - 1)
    checks = Check.objects.filter(created_at__date__gte=start_day)
    if not request.user.is_staff:
        checks = checks.filter(user=request.user)

    categories = dict(checks.order_by().values_list("category").annotate(n=Count("id")))
    types = dict(checks.order_by().values_list("check_type").annotate(n=Count("id")))
    levels = dict(checks.order_by().values_list("risk_level").annotate(n=Count("id")))
    per_day = {
        row["day"]: row["n"]
        for row in checks.order_by().annotate(day=TruncDate("created_at")).values("day").annotate(n=Count("id"))
    }
    top_features = (
        DetectedFeature.objects.filter(check_ref__in=checks)
        .order_by()
        .values("title")
        .annotate(n=Count("id"))
        .order_by("-n", "title")[:TOP_FEATURES]
    )

    payload = {
        "days": days,
        "is_admin": request.user.is_staff,
        "total": sum(categories.values()),
        "total_sms": types.get("SMS", 0),
        "total_url": types.get("URL", 0),
        "safe": categories.get("SAFE", 0),
        "suspicious": categories.get("SUSPICIOUS", 0),
        "fraudulent": categories.get("FRAUDULENT", 0) + categories.get("DANGEROUS", 0),
        "average_score": round(checks.aggregate(v=Avg("risk_score"))["v"] or 0),
        "levels": {"LOW": levels.get("LOW", 0), "MEDIUM": levels.get("MEDIUM", 0), "HIGH": levels.get("HIGH", 0)},
        "per_day": [
            {"date": day.isoformat(), "count": per_day.get(day, 0)}
            for day in (start_day + timedelta(days=i) for i in range(days))
        ],
        "top_features": [{"title": row["title"], "count": row["n"]} for row in top_features],
    }
    if not request.user.is_staff:
        # Администратор получает только агрегаты: чужие тексты SMS ему не показываются (ФТ-1.9).
        payload["recent"] = [
            {
                "id": check.id,
                "url": reverse("result", args=[check.id]),
                "created_at": check.created_at.isoformat(),
                "type": check.check_type,
                "fragment": check_fragment(check),
                "category": check.category,
                "risk_score": check.risk_score,
            }
            for check in checks[:RECENT_LIMIT]
        ]
    else:
        payload["recent"] = []
    return Response(payload)
