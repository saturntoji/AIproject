import pytest

from ml.language import detect_language
from ml.predictor import predict_sms
from ml.rules import RULE_GROUPS, find_rule_groups


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


def test_predict_sms_returns_label_and_probability():
    result = predict_sms("Congratulations! You won a $1000 gift card. Claim your prize now")
    assert set(result) == {"label", "probability"}
    assert result["label"] == 1
    assert predict_sms("See you at the library tomorrow")["label"] == 0
