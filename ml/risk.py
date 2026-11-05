"""Расчёт Risk Score по формуле задания 13. Веса и пороги лежат в risk_config.yaml."""
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from ml.rules import RULES_BY_CODE

CONFIG_PATH = Path(__file__).resolve().parents[1] / "risk_config.yaml"
LEVEL_TO_CATEGORY = {"LOW": "SAFE", "MEDIUM": "SUSPICIOUS", "HIGH": "FRAUDULENT"}
MAX_REASONS = 6


@lru_cache(maxsize=1)
def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


@dataclass
class RiskResult:
    score: int
    level: str
    category: str
    reasons: list[str] = field(default_factory=list)
    recommendation: str = ""


def level_for_score(score: float, config: dict | None = None) -> str:
    levels = (config or load_config())["levels"]
    if score >= levels["high_from"]:
        return "HIGH"
    if score >= levels["medium_from"]:
        return "MEDIUM"
    return "LOW"


def url_category(p_url: float, config: dict | None = None) -> str:
    thresholds = (config or load_config())["url_categories"]
    if p_url >= thresholds["t2"]:
        return "DANGEROUS"
    if p_url >= thresholds["t1"]:
        return "SUSPICIOUS"
    return "SAFE"


def heuristic_p_url(features: dict, config: dict | None = None) -> float:
    """Прототип оценки URL до обучения модели в задании 11."""
    weights = (config or load_config())["url_heuristic"]
    total = sum(weights[code] for code in (
        "has_ip", "has_punycode", "mixed_alphabets", "brand_lookalike", "has_at", "is_shortener",
        "suspicious_tld", "nonstandard_port", "double_slash_in_path",
    ) if features[code])
    total += weights["per_suspicious_word"] * features["suspicious_word_count"]
    total += weights["many_hyphens"] * (features["hyphen_count"] >= 2)
    total += weights["many_subdomains"] * (features["subdomain_count"] >= 3)
    total += weights["no_https"] * (not features["is_https"])
    return round(1 - math.exp(-total), 4)


def compute_risk(
    p_sms: float | None,
    p_url_max: float | None,
    se_groups: list[str] | None,
    url_flags: list[str] | None = None,
    url_reasons: list[str] | None = None,
    config: dict | None = None,
) -> RiskResult:
    """Объединить оценки. Слагаемое с None исключается из числителя и знаменателя.

    p_sms=None — текст не анализировался или ML ненадёжна для языка;
    se_groups=None — проверяется отдельная ссылка, текста нет.
    """
    config = config or load_config()
    weights = config["weights"]
    overrides = config["overrides"]
    url_flags = url_flags or []

    numerator = denominator = 0.0
    if se_groups is not None:
        s_se = min(len(se_groups) / config["social_engineering_saturation"], 1.0)
        numerator += weights["social_engineering"] * s_se
        denominator += weights["social_engineering"]
    se_groups = se_groups or []
    if p_sms is not None:
        numerator += weights["sms"] * p_sms
        denominator += weights["sms"]
    if p_url_max is not None:
        numerator += weights["url"] * p_url_max
        denominator += weights["url"]
    score = 100 * numerator / denominator

    if "CODE_REQUEST" in se_groups:
        score = max(score, overrides["code_request_min"])
    t2 = config["url_categories"]["t2"]
    if p_sms is not None and p_url_max is not None and p_sms >= overrides["sms_threshold"] and p_url_max >= t2:
        score = max(score, overrides["sms_and_url_min"])
    if "has_ip" in url_flags or "has_punycode" in url_flags:
        score = max(score, overrides["url_masking_min"])

    score = int(round(min(score, 100)))
    level = level_for_score(score, config)
    return RiskResult(
        score=score,
        level=level,
        category=LEVEL_TO_CATEGORY[level],
        reasons=_build_reasons(p_sms, p_url_max, se_groups, url_reasons or [], level),
        recommendation=config["recommendations"][level],
    )


def _build_reasons(p_sms, p_url_max, se_groups, url_reasons, level) -> list[str]:
    weighted = []
    if p_sms is not None and p_sms > 0.5:
        weighted.append((p_sms, f"Текстовая модель считает сообщение похожим на спам ({p_sms:.0%})"))
    for code in se_groups:
        weighted.append((0.6, RULES_BY_CODE[code].reason))
    if p_url_max is not None and p_url_max > 0.5:
        weighted.append((p_url_max, f"Ссылка имеет подозрительную структуру ({p_url_max:.0%})"))
    weighted.extend((0.5, reason) for reason in url_reasons)
    weighted.sort(key=lambda item: item[0], reverse=True)
    reasons = [text for _, text in weighted][:MAX_REASONS]
    if not reasons:
        reasons = ["Признаков мошенничества не обнаружено"] if level == "LOW" else ["Совокупность слабых признаков"]
    return reasons
