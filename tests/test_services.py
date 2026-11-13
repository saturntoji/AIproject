"""Задание 12: интеграционные тесты сервиса анализа."""
from apps.analysis.services import AnalysisResult, analyze_sms, analyze_url


def test_sms_without_url():
    result = analyze_sms("Мама, срочно переведи 50 000 на этот номер, никому не говори.")
    assert isinstance(result, AnalysisResult)
    assert result.urls == [] and result.p_url_max is None
    assert result.p_sms is not None and result.explanation and result.recommendation


def test_sms_with_one_url():
    result = analyze_sms("Ваша карта заблокирована! Срочно подтвердите данные: http://secure-bank-verify.example/login")
    assert len(result.urls) == 1
    assert result.urls[0].domain == "secure-bank-verify.example"
    assert result.p_url_max == result.urls[0].p_url
    assert result.category == "FRAUDULENT"


def test_sms_with_three_urls_and_extra_ignored():
    text = "a http://one.example b www.two.example c bit.ly/three d http://four.example"
    result = analyze_sms(text)
    assert [u.url for u in result.urls] == ["http://one.example", "www.two.example", "bit.ly/three"]
    assert result.p_url_max == max(u.p_url for u in result.urls)


def test_url_only():
    result = analyze_url("http://192.0.2.15/account-update")
    assert result.type == "URL" and result.p_sms is None
    assert result.risk_score >= 60
    assert result.model_versions["url"] == "1.0.0"
