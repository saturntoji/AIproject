"""Задание 9: признаки URL на синтетических адресах зарезервированных доменов."""
import ast
from pathlib import Path

import pytest

from ml.url_features import (
    FEATURE_NAMES,
    MODEL_FEATURES,
    canonical_url,
    explain_url,
    extract_url_features,
    extract_urls,
    model_features,
    validate_url,
)


def test_at_least_twenty_features_in_fixed_order():
    assert len(FEATURE_NAMES) >= 20
    assert list(extract_url_features("https://www.example.com/a?x=1")) == FEATURE_NAMES


@pytest.mark.parametrize("url", ["", "   ", None, "ftp://example.com", "nodomain", "http://", "a b.example", "x" * 3000])
def test_validate_url_rejects_bad_input(url):
    assert validate_url(url)[1] is not None


@pytest.mark.parametrize("url", ["", None, "http://", "\x00\x01"])
def test_bad_input_gives_zero_features_without_exception(url):
    assert set(extract_url_features(url).values()) == {0}


def test_url_without_scheme_is_parsed_as_http():
    assert validate_url("example.com/a") == ("http://example.com/a", None)
    assert extract_url_features("example.com")["is_https"] == 0


def test_lengths_and_counts():
    features = extract_url_features("https://a-b.example.com/path/to?x=1&y=2")
    assert features["host_length"] == len("a-b.example.com")
    assert features["path_length"] == len("/path/to")
    assert features["hyphen_count"] == 1
    assert features["query_param_count"] == 2
    assert features["is_https"] == 1


def test_ipv4_and_ipv6():
    assert extract_url_features("http://192.0.2.15/login")["has_ip"] == 1
    assert extract_url_features("http://[2001:db8::1]/login")["has_ip"] == 1
    assert extract_url_features("http://example.org")["has_ip"] == 0


def test_port_at_and_double_slash():
    features = extract_url_features("http://user@example.org:8080/a//b")
    assert features["nonstandard_port"] == 1
    assert features["has_at"] == 1
    assert features["double_slash_in_path"] == 1
    assert extract_url_features("https://example.org:443/")["nonstandard_port"] == 0


def test_shortener_and_free_hosting():
    assert extract_url_features("bit.ly/test")["is_shortener"] == 1
    assert extract_url_features("http://clck.ru/abc")["is_shortener"] == 1
    assert extract_url_features("https://login.firebaseapp.com")["free_hosting"] == 1


def test_suspicious_words_and_tld():
    features = extract_url_features("http://secure-login-verify.top/account")
    assert features["suspicious_word_count"] >= 3
    assert features["suspicious_tld"] == 1


def test_brand_name_on_own_site_is_not_suspicious():
    assert extract_url_features("https://halykbank.kz")["suspicious_word_count"] == 0
    assert extract_url_features("https://kaspi.kz/shop")["brand_lookalike"] == 0


def test_brand_lookalike_and_punycode():
    assert extract_url_features("http://kaspii.example/")["brand_lookalike"] == 1
    assert extract_url_features("http://xn--exmple-cua.test/")["has_punycode"] == 1


def test_mixed_alphabets():
    # Вторая буква — кириллическая «а».
    assert extract_url_features("http://kаspi.test")["mixed_alphabets"] == 1


def test_subdomains_on_reserved_zone():
    assert extract_url_features("http://a.b.bank.example/")["subdomain_count"] == 2


def test_explain_url_gives_russian_reasons():
    reasons = explain_url(extract_url_features("http://192.0.2.15/account-update"))
    assert "Используется IP-адрес вместо доменного имени" in reasons
    assert explain_url(extract_url_features("https://example.org")) == []


def test_extract_urls_limit_and_forms():
    text = "a http://one.example b www.two.example c bit.ly/three d http://four.example"
    assert extract_urls(text) == ["http://one.example", "www.two.example", "bit.ly/three"]


def test_canonical_url_keeps_only_domain():
    assert canonical_url("https://www.Example.com/about?x=1") == "http://example.com"
    assert canonical_url("user@evil.example:8080/login") == "http://evil.example:8080"
    assert canonical_url("") == ""


def test_model_gets_same_features_for_any_scheme_or_path():
    assert model_features("https://www.example.com/a/b?c=1") == model_features("example.com")
    assert list(model_features("example.com")) == MODEL_FEATURES


def test_module_has_no_network_calls():
    tree = ast.parse(Path("ml/url_features.py").read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert not modules & {"requests", "socket", "urllib3", "http", "httpx"}
