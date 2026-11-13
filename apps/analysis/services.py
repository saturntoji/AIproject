"""Сервис анализа (задание 12): объединяет модели, правила и риск, сохраняет результат."""
import logging
import re
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.analysis.models import Check, DetectedFeature, UrlResult
from ml import predictor
from ml.language import TRAINED_LANGUAGES, detect_language
from ml.preprocessing import MONEY_RE
from ml.risk import compute_risk, load_config, url_category
from ml.rules import RULES_BY_CODE, find_rule_groups
from ml.url_features import (
    FEATURE_TITLES,
    FLAG_FEATURES,
    explain_url,
    extract_url_features,
    extract_urls,
    get_host,
    model_features,
    triggered_features,
    validate_url,
)

logger = logging.getLogger(__name__)
URL_CATEGORY_BY_LEVEL = {"LOW": "SAFE", "MEDIUM": "SUSPICIOUS", "HIGH": "DANGEROUS"}
# Любая группа цифр, в которой не меньше 4 цифр: телефоны, карты, суммы и коды.
_LONG_NUMBER_RE = re.compile(r"\+?\d(?:[\s().-]?\d){3,}")
DUPLICATE_WINDOW = timedelta(seconds=10)

LANGUAGE_WARNING = (
    "Текстовая модель обучена только на английских SMS, поэтому для этого языка её оценка "
    "ненадёжна и в Risk Score не учитывается. Работают словарь правил и анализ ссылок."
)


@dataclass
class UrlAnalysis:
    url: str
    domain: str
    p_url: float
    category: str
    features: dict
    reasons: list[str]


@dataclass
class AnalysisResult:
    """Поля совпадают с ответом API из раздела 4.4; id и created_at появляются после сохранения."""

    type: str
    language: str
    category: str
    risk_level: str
    risk_score: int
    p_sms: float | None
    p_url_max: float | None = None
    urls: list[UrlAnalysis] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    recommendation: str = ""
    disclaimer: str = ""
    model_versions: dict = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None


def _url_thresholds() -> tuple[float, float]:
    meta = predictor.load_url_meta()
    fallback = load_config()["url_categories"]
    return meta.get("t1", fallback["t1"]), meta.get("t2", fallback["t2"])


OFFICIAL_DOMAIN_REASON = "Домен входит в список официальных доменов банков и сервисов"


def _analyze_single_url(url: str) -> UrlAnalysis:
    features = extract_url_features(url)
    p_url = predictor.predict_url(model_features(url))
    t1, t2 = _url_thresholds()
    reasons = explain_url(features)
    if features["official_domain"]:
        # Модель видит только строку домена и не знает, что это сайт самого банка: ограничиваем оценку правилом.
        p_url = min(p_url, round(t1 * 0.9, 4))
        reasons = [OFFICIAL_DOMAIN_REASON, *reasons]
    return UrlAnalysis(
        url=url,
        domain=get_host(url),
        p_url=p_url,
        category=url_category(p_url, t1, t2),
        features=features,
        reasons=reasons,
    )


def _model_versions(has_text: bool, has_urls: bool) -> dict:
    return {
        "sms": predictor.load_sms_meta().get("version", "") if has_text else "",
        "url": predictor.load_url_meta().get("version", "") if has_urls else "",
    }


def analyze_sms(text: str) -> AnalysisResult:
    language = detect_language(text)
    p_sms = predictor.predict_sms(text)["probability"]
    groups = find_rule_groups(text)
    # Адреса с ошибками формата пропускаем: остальной текст всё равно нужно оценить.
    urls = [_analyze_single_url(u) for u in extract_urls(text) if validate_url(u)[1] is None]
    p_url_max = max((u.p_url for u in urls), default=None)
    flags = [code for u in urls for code in triggered_features(u.features)]
    reasons = list(dict.fromkeys(reason for u in urls for reason in u.reasons))
    risk = compute_risk(
        p_sms if language in TRAINED_LANGUAGES else None,
        p_url_max,
        groups,
        url_flags=flags,
        url_reasons=reasons,
        url_t2=_url_thresholds()[1],
    )
    return AnalysisResult(
        type=Check.TYPE_SMS,
        language=language,
        category=risk.category,
        risk_level=risk.level,
        risk_score=risk.score,
        p_sms=p_sms,
        p_url_max=p_url_max,
        urls=urls,
        features=groups,
        explanation=risk.reasons,
        recommendation=risk.recommendation,
        disclaimer=load_config()["disclaimer"],
        model_versions=_model_versions(True, bool(urls)),
    )


def analyze_url(url: str) -> AnalysisResult:
    item = _analyze_single_url(url)
    risk = compute_risk(
        None,
        item.p_url,
        None,
        url_flags=triggered_features(item.features),
        url_reasons=item.reasons,
        url_t1=_url_thresholds()[0],
        url_t2=_url_thresholds()[1],
    )
    item.category = URL_CATEGORY_BY_LEVEL[risk.level]
    return AnalysisResult(
        type=Check.TYPE_URL,
        language="other",
        category=item.category,
        risk_level=risk.level,
        risk_score=risk.score,
        p_sms=None,
        p_url_max=item.p_url,
        urls=[item],
        explanation=risk.reasons,
        recommendation=risk.recommendation,
        disclaimer=load_config()["disclaimer"],
        model_versions=_model_versions(False, True),
    )


def mask_sensitive(text: str) -> str:
    """Заменить суммы, номера телефонов и карт на ***."""
    text = MONEY_RE.sub("***", text)
    return _LONG_NUMBER_RE.sub("***", text)


def find_recent_duplicate(user, check_type: str, raw_input: str) -> Check | None:
    """Повторная отправка той же формы за несколько секунд возвращает уже сохранённую проверку (НФТ-3)."""
    masked = mask_sensitive(raw_input) if check_type == Check.TYPE_SMS else raw_input
    return (
        Check.objects.filter(
            user=user,
            check_type=check_type,
            input_masked=masked,
            created_at__gte=timezone.now() - DUPLICATE_WINDOW,
        )
        .order_by("-created_at")
        .first()
    )


def save_check(user, result: AnalysisResult, raw_input: str) -> Check:
    is_sms = result.type == Check.TYPE_SMS
    keep_text = not is_sms or UserProfile.for_user(user).store_sms_text
    with transaction.atomic():
        check = Check.objects.create(
            user=user,
            check_type=result.type,
            input_text=raw_input if keep_text else None,
            input_masked=mask_sensitive(raw_input) if is_sms else raw_input,
            language=result.language,
            category=result.category,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            p_sms=result.p_sms,
            explanation=result.explanation,
            recommendation=result.recommendation,
            sms_model_version=result.model_versions.get("sms", ""),
            url_model_version=result.model_versions.get("url", ""),
        )
        UrlResult.objects.bulk_create(
            UrlResult(
                check_ref=check,
                url=u.url,
                domain=u.domain,
                p_url=u.p_url,
                category=u.category,
                features_json=u.features,
            )
            for u in result.urls
        )
        DetectedFeature.objects.bulk_create(
            DetectedFeature(check_ref=check, code=code, title=RULES_BY_CODE[code].title)
            for code in result.features
        )
    # В лог попадают только id и категория: текст SMS сюда не пишется (НФТ-9).
    logger.info("check id=%s type=%s category=%s", check.id, check.check_type, check.category)
    return check


def check_to_dict(check: Check) -> dict:
    """Единый формат результата для API и страницы подробного результата."""
    warnings = []
    is_sms = check.check_type == Check.TYPE_SMS
    if is_sms and check.language not in TRAINED_LANGUAGES:
        warnings.append(LANGUAGE_WARNING)
    urls = []
    for item in check.url_results.all():
        triggered = set(triggered_features(item.features_json))
        urls.append(
            {
                "url": item.url,
                "domain": item.domain,
                "p_url": item.p_url,
                "category": item.category,
                "feature_table": [
                    {
                        "code": code,
                        "title": title,
                        "value": item.features_json.get(code, 0),
                        "triggered": code in triggered,
                        "is_flag": code in FLAG_FEATURES,
                    }
                    for code, title in FEATURE_TITLES.items()
                ],
            }
        )
    return {
        "id": check.id,
        "type": check.check_type,
        "input": check.input_text if check.input_text is not None else check.input_masked,
        "is_masked": check.input_text is None,
        "language": check.language,
        "category": check.category,
        "risk_level": check.risk_level,
        "risk_score": check.risk_score,
        "p_sms": check.p_sms,
        "p_sms_reliable": is_sms and check.language in TRAINED_LANGUAGES,
        "p_url_max": max((u["p_url"] for u in urls), default=None),
        "urls": urls,
        "features": [{"code": f.code, "title": f.title} for f in check.detected_features.all()],
        "explanation": check.explanation,
        "recommendation": check.recommendation,
        "warnings": warnings,
        "disclaimer": load_config()["disclaimer"],
        "model_versions": {"sms": check.sms_model_version, "url": check.url_model_version},
        "created_at": check.created_at.isoformat(),
    }


def check_fragment(check: Check, limit: int = 60) -> str:
    """Короткий фрагмент для таблиц: полный текст, только если есть согласие."""
    text = check.input_text if check.input_text is not None else check.input_masked
    return text if len(text) <= limit else f"{text[:limit]}…"


def filter_checks(queryset, params):
    """Фильтры истории: date_from, date_to, type, category, risk_level."""
    from django.utils.dateparse import parse_date

    date_from = parse_date(params.get("date_from") or "") if _is_date(params.get("date_from")) else None
    date_to = parse_date(params.get("date_to") or "") if _is_date(params.get("date_to")) else None
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    if params.get("type") in (Check.TYPE_SMS, Check.TYPE_URL):
        queryset = queryset.filter(check_type=params["type"])
    category = params.get("category")
    if category == "FRAUDULENT":
        queryset = queryset.filter(category__in=["FRAUDULENT", "DANGEROUS"])
    elif category in ("SAFE", "SUSPICIOUS"):
        queryset = queryset.filter(category=category)
    if params.get("risk_level") in ("LOW", "MEDIUM", "HIGH"):
        queryset = queryset.filter(risk_level=params["risk_level"])
    return queryset


def _is_date(value) -> bool:
    return bool(value) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
