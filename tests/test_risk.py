"""Задание 13: граничные значения Risk Score."""
import copy

import pytest

from ml.risk import LEVEL_TO_CATEGORY, MAX_REASONS, compute_risk, level_for_score, load_config, url_category


@pytest.fixture
def config():
    """Начальные веса из ТЗ, чтобы ожидаемые числа не зависели от калибровки."""
    cfg = copy.deepcopy(load_config())
    cfg["weights"] = {"sms": 0.5, "url": 0.3, "social_engineering": 0.2}
    cfg["social_engineering_saturation"] = 3
    cfg["levels"] = {"medium_from": 35, "high_from": 70}
    return cfg


@pytest.mark.parametrize("score, level", [(0, "LOW"), (34, "LOW"), (35, "MEDIUM"), (69, "MEDIUM"), (70, "HIGH"), (100, "HIGH")])
def test_level_boundaries(config, score, level):
    assert level_for_score(score, config) == level


def test_levels_map_to_categories():
    assert LEVEL_TO_CATEGORY == {"LOW": "SAFE", "MEDIUM": "SUSPICIOUS", "HIGH": "FRAUDULENT"}


def test_formula_without_url(config):
    # 100 * (0.5 * 0.5 + 0.2 * 0) / (0.5 + 0.2) = 35.7
    assert compute_risk(0.5, None, [], config=config).score == 36


def test_formula_with_url(config):
    # 100 * (0.5 * 0.2 + 0.3 * 0.4 + 0.2 * 1/3) / 1.0 = 28.7
    assert compute_risk(0.2, 0.4, ["URGENCY"], config=config).score == 29


def test_url_only_check_uses_url_probability(config):
    assert compute_risk(None, 0.42, None, config=config).score == 42


def test_social_engineering_saturates(config):
    assert compute_risk(None, None, ["URGENCY", "PRIZE", "SECRECY", "BANK_CARD"], config=config).score == 100


def test_code_request_override(config):
    assert compute_risk(0.0, None, ["CODE_REQUEST"], config=config).score >= 70


def test_sms_and_url_override(config):
    assert compute_risk(0.8, 0.7, [], url_t2=0.7, config=config).score >= 85
    assert compute_risk(0.79, 0.7, [], url_t2=0.7, config=config).score < 85


def test_ip_or_punycode_override(config):
    assert compute_risk(0.0, 0.1, [], url_flags=["has_ip"], config=config).score >= 60
    assert compute_risk(0.0, 0.1, [], url_flags=["has_punycode"], config=config).score >= 60


def test_all_signals_at_once(config):
    risk = compute_risk(
        1.0, 1.0, ["URGENCY", "CODE_REQUEST", "PRIZE"], url_flags=["has_ip"], url_reasons=["a", "b", "c", "d"], config=config
    )
    assert risk.score == 100 and risk.level == "HIGH"
    assert len(risk.reasons) == MAX_REASONS


def test_every_result_has_reason_and_recommendation(config):
    for args in [(0.0, None, []), (0.5, 0.5, ["URGENCY"]), (1.0, None, ["CODE_REQUEST"])]:
        risk = compute_risk(*args, config=config)
        assert risk.reasons and risk.recommendation


def test_reasons_sorted_by_contribution(config):
    risk = compute_risk(0.95, None, ["URGENCY"], config=config)
    assert risk.reasons[0].startswith("Текстовая модель")


def test_config_change_changes_result(config):
    before = compute_risk(0.5, None, [], config=config).score
    config["weights"]["sms"] = 0.9
    assert compute_risk(0.5, None, [], config=config).score != before


def test_url_category_thresholds():
    assert url_category(0.1, 0.3, 0.6) == "SAFE"
    assert url_category(0.3, 0.3, 0.6) == "SUSPICIOUS"
    assert url_category(0.6, 0.3, 0.6) == "DANGEROUS"
