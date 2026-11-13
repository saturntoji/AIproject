"""Расчёт Risk Score по формуле задания 13. Веса и пороги лежат в risk_config.yaml."""
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


def url_category(p_url: float, t1: float | None = None, t2: float | None = None) -> str:
    """Категория ссылки. Пороги t1 и t2 подобраны на валидации и хранятся в url_model_meta.json."""
    fallback = load_config()["url_categories"]
    t1 = fallback["t1"] if t1 is None else t1
    t2 = fallback["t2"] if t2 is None else t2
    if p_url >= t2:
        return "DANGEROUS"
    if p_url >= t1:
        return "SUSPICIOUS"
    return "SAFE"


def url_only_score(p_url: float, t1: float | None, t2: float | None, config: dict) -> float:
    """Кусочно-линейно переводит P_url в баллы: [0, t1) → низкий, [t1, t2) → средний, [t2, 1] → высокий."""
    t1 = config["url_categories"]["t1"] if t1 is None else t1
    t2 = config["url_categories"]["t2"] if t2 is None else t2
    medium, high = config["levels"]["medium_from"], config["levels"]["high_from"]
    if p_url < t1:
        return medium * p_url / t1
    if p_url < t2:
        return medium + (high - medium) * (p_url - t1) / (t2 - t1)
    return high + (100 - high) * (p_url - t2) / (1 - t2)


def compute_risk(
    p_sms: float | None,
    p_url_max: float | None,
    se_groups: list[str] | None,
    url_flags: list[str] | None = None,
    url_reasons: list[str] | None = None,
    url_t1: float | None = None,
    url_t2: float | None = None,
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

    url_only = p_sms is None and se_groups is None and p_url_max is not None
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
    if url_only:
        # Отдельная ссылка: баллы считаются так, чтобы пороги категорий t1 и t2 совпали с границами уровней.
        score = url_only_score(p_url_max, url_t1, url_t2, config)
    else:
        score = 100 * numerator / denominator

    if "CODE_REQUEST" in se_groups:
        score = max(score, overrides["code_request_min"])
    t2 = config["url_categories"]["t2"] if url_t2 is None else url_t2
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
