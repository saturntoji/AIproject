"""Сервис анализа: объединяет модели, правила и риск, сохраняет результат."""
import logging
import re
from dataclasses import dataclass, field

from django.db import transaction

from apps.accounts.models import UserProfile
from apps.analysis.models import Check, DetectedFeature, UrlResult
from ml import predictor
from ml.language import TRAINED_LANGUAGES, detect_language
from ml.preprocessing import MONEY_RE
from ml.risk import compute_risk, heuristic_p_url, load_config, url_category
from ml.rules import RULES_BY_CODE, find_rule_groups
from ml.url_features import (
    FEATURE_TITLES,
    FLAG_FEATURES,
    explain_url,
    extract_url_features,
    extract_urls,
    get_host,
    triggered_features,
    validate_url,
)

logger = logging.getLogger(__name__)
URL_MODEL_VERSION = "heuristic-prototype"
_LOW_RISK_URL = {"LOW": "SAFE", "MEDIUM": "SUSPICIOUS", "HIGH": "DANGEROUS"}
_CARD_OR_PHONE_RE = re.compile(r"(?<![\w.])\+?\d[\d\s().-]{7,}\d(?!\w)")

LANGUAGE_WARNING = (
    "Текстовая модель обучена только на английских SMS, поэтому для этого языка её оценка "
    "ненадёжна и в Risk Score не учитывается. Работают словарь правил и анализ ссылок."
)
URL_PROTOTYPE_NOTE = (
    "Прототип: P_url рассчитана по правилам из risk_config.yaml. URL-модель обучается в задании 11."
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
    check_type: str
    language: str
    category: str
    risk_level: str
    risk_score: int
    p_sms: float | None
    urls: list[UrlAnalysis] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    recommendation: str = ""


def _analyze_single_url(url: str) -> UrlAnalysis:
    features = extract_url_features(url)
    p_url = heuristic_p_url(features)
    return UrlAnalysis(
        url=url,
        domain=get_host(url),
        p_url=p_url,
        category=url_category(p_url),
        features=features,
        reasons=explain_url(features),
    )


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
    )
    return AnalysisResult(
        check_type=Check.TYPE_SMS,
        language=language,
        category=risk.category,
        risk_level=risk.level,
        risk_score=risk.score,
        p_sms=p_sms,
        urls=urls,
        features=groups,
        explanation=risk.reasons,
        recommendation=risk.recommendation,
    )


def analyze_url(url: str) -> AnalysisResult:
    item = _analyze_single_url(url)
    risk = compute_risk(
        None,
        item.p_url,
        None,
        url_flags=triggered_features(item.features),
        url_reasons=item.reasons,
    )
    item.category = _LOW_RISK_URL[risk.level]
    return AnalysisResult(
        check_type=Check.TYPE_URL,
        language="other",
        category=item.category,
        risk_level=risk.level,
        risk_score=risk.score,
        p_sms=None,
        urls=[item],
        explanation=risk.reasons,
        recommendation=risk.recommendation,
    )


def mask_sensitive(text: str) -> str:
    """Заменить суммы, номера телефонов и карт на ***."""
    text = MONEY_RE.sub("***", text)
    return _CARD_OR_PHONE_RE.sub("***", text)


def save_check(user, result: AnalysisResult, raw_input: str) -> Check:
    is_sms = result.check_type == Check.TYPE_SMS
    keep_text = not is_sms or UserProfile.for_user(user).store_sms_text
    with transaction.atomic():
        check = Check.objects.create(
            user=user,
            check_type=result.check_type,
            input_text=raw_input if keep_text else None,
            input_masked=mask_sensitive(raw_input) if is_sms else raw_input,
            language=result.language,
            category=result.category,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            p_sms=result.p_sms,
            explanation=result.explanation,
            recommendation=result.recommendation,
            sms_model_version=predictor.load_sms_meta().get("version", "") if is_sms else "",
            url_model_version=URL_MODEL_VERSION if result.urls else "",
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
    if urls:
        warnings.append(URL_PROTOTYPE_NOTE)
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
