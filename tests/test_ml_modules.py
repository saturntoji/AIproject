import pytest

from ml.language import detect_language
from ml.predictor import predict_sms
from ml.risk import compute_risk, heuristic_p_url, level_for_score
from ml.rules import RULE_GROUPS, find_rule_groups
from ml.url_features import FEATURE_NAMES, extract_url_features, extract_urls, validate_url


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Привет, как дела?", "ru"),
        ("Сәлем! Ертең кездесеміз бе?", "kk"),
        ("Your order has been shipped", "en"),
        ("12345 !!!", "other"),
        ("Bonjour, ça va très bien", "other"),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_rules_have_enough_groups_and_phrases():
    assert len(RULE_GROUPS) >= 6
    assert all(len(group.phrases) >= 30 for group in RULE_GROUPS)


def test_otp_notice_is_not_code_request():
    assert "CODE_REQUEST" not in find_rule_groups("Ваш код подтверждения: 4821. Никому не сообщайте этот код.")


def test_code_request_found():
    assert "CODE_REQUEST" in find_rule_groups("Назовите код из SMS для отмены операции")


def test_word_boundary():
    assert "PRIZE" not in find_rule_groups("My sister is a surprizes fan")


def test_extract_urls_limit_and_forms():
    text = "a http://one.example b www.two.example c bit.ly/three d http://four.example"
    assert extract_urls(text) == ["http://one.example", "www.two.example", "bit.ly/three"]


@pytest.mark.parametrize("url", ["", "   ", "ftp://example.com", "nodomain", "http://", "a b.example"])
def test_validate_url_rejects(url):
    assert validate_url(url)[1] is not None


def test_validate_url_adds_scheme_for_parsing():
    assert validate_url("example.com/a") == ("http://example.com/a", None)


def test_features_keep_fixed_order_and_handle_bad_input():
    assert list(extract_url_features("https://www.example.com")) == FEATURE_NAMES
    assert list(extract_url_features("")) == FEATURE_NAMES
    assert len(FEATURE_NAMES) >= 20


def test_ip_and_port_and_at():
    features = extract_url_features("http://192.0.2.15:8080/a@b")
    assert features["has_ip"] == 1
    assert features["nonstandard_port"] == 1
    assert features["has_at"] == 1


def test_shortener_and_punycode():
    assert extract_url_features("bit.ly/test")["is_shortener"] == 1
    assert extract_url_features("http://xn--exmple-cua.test/")["has_punycode"] == 1


def test_reserved_domain_subdomains():
    assert extract_url_features("http://a.b.bank.example/")["subdomain_count"] == 2


def test_brand_lookalike():
    assert extract_url_features("http://kaspii.example/")["brand_lookalike"] == 1
    assert extract_url_features("https://kaspi.kz/")["brand_lookalike"] == 0


def test_safe_url_scores_lower_than_phishing():
    safe = heuristic_p_url(extract_url_features("https://www.example.com/about"))
    bad = heuristic_p_url(extract_url_features("http://secure-bank-verify.example/login"))
    assert safe < 0.35 <= bad


@pytest.mark.parametrize("score, level", [(34, "LOW"), (35, "MEDIUM"), (69, "MEDIUM"), (70, "HIGH")])
def test_risk_level_boundaries(score, level):
    assert level_for_score(score) == level


def test_formula_without_url():
    # 100 * (0.5 * 0.5 + 0.2 * 0) / (0.5 + 0.2)
    assert compute_risk(0.5, None, []).score == 36


def test_code_request_override():
    assert compute_risk(0.0, None, ["CODE_REQUEST"]).score >= 70


def test_sms_and_url_override():
    assert compute_risk(0.8, 0.7, []).score >= 85


def test_url_masking_override():
    assert compute_risk(0.0, 0.1, [], url_flags=["has_ip"]).score >= 60


def test_every_result_has_reason_and_recommendation():
    risk = compute_risk(0.0, None, [])
    assert risk.reasons and risk.recommendation


def test_predict_sms_returns_label_and_probability():
    result = predict_sms("Congratulations! You won a $1000 gift card. Claim your prize now")
    assert set(result) == {"label", "probability"}
    assert result["label"] == 1
    assert predict_sms("See you at the library tomorrow")["label"] == 0
