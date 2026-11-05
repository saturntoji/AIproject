import pandas as pd

from ml.data.clean_sms import clean_dataframe
from ml.preprocessing import normalize_sms


def test_empty_string():
    assert normalize_sms("") == ""
    assert normalize_sms("   \n\t ") == ""


def test_non_string_input():
    assert normalize_sms(None) == ""
    assert normalize_sms(123) == ""


def test_only_url():
    assert normalize_sms("http://secure-bank-verify.example/login") == "<url>"
    assert normalize_sms("www.example.com") == "<url>"


def test_bare_shortener_url():
    assert normalize_sms("Claim: bit.ly/prize-claim-test") == "claim: <url>"


def test_glued_sentence_is_not_url():
    assert "<url>" not in normalize_sms("Ok.I will call you later")


def test_mixed_case():
    assert normalize_sms("HeLLo WoRLD") == "hello world"


def test_cyrillic_kept():
    assert normalize_sms("Привет, МИР") == "привет, мир"


def test_kazakh_letters_kept():
    assert normalize_sms("ӘҒҚҢӨҰҮҺІ") == "әғқңөұүһі"


def test_money_with_currency_symbols():
    assert normalize_sms("£1000") == "<money>"
    assert normalize_sms("$50") == "<money>"
    assert normalize_sms("350 ₸") == "<money>"
    assert normalize_sms("50 000 тг") == "<money>"
    assert normalize_sms("1 000 руб") == "<money>"
    assert normalize_sms("150p/msg") == "<money> /msg"


def test_phones():
    assert normalize_sms("+7 (700) 000-00-00") == "<phone>"
    assert normalize_sms("Call 09061701461 now") == "call <phone> now"


def test_short_numbers_are_num():
    assert normalize_sms("Order 4821") == "order <num>"
    assert normalize_sms("18:00") == "<num> : <num>"


def test_email():
    assert normalize_sms("write to user@example.com") == "write to <email>"


def test_emoji_kept():
    assert "😀" in normalize_sms("Привет 😀")


def test_pressure_marks_are_separate_tokens():
    assert normalize_sms("Срочно!!") == "срочно ! !"
    assert normalize_sms("Why?") == "why ?"


def test_control_chars_and_spaces():
    assert normalize_sms("a\x00b\n\n  c\t\td") == "ab c d"


def test_function_is_deterministic():
    text = "URGENT! Call +7 700 000 00 00"
    assert normalize_sms(text) == normalize_sms(text)


def test_clean_dataframe_counts_duplicates_per_class():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "text": ["Hello", "HELLO", "Win $5", "   "],
            "label": [0, 0, 1, 1],
        }
    )
    clean, _, removed = clean_dataframe(df)
    assert list(clean["id"]) == [1, 3]
    assert removed == {0: 1, 1: 0}
