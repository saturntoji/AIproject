import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import UserProfile
from apps.analysis.models import Check

PASSWORD = "Password123"
FRAUD_SMS = "Ваша карта заблокирована! Срочно подтвердите данные по ссылке: http://secure-bank-verify.example/login"
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def user():
    return get_user_model().objects.create_user("tester", "tester@example.com", PASSWORD)


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def test_health_is_public():
    response = Client().get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/", "/check/sms/", "/check/url/", "/history/", "/stats/", "/profile/"])
def test_pages_require_login(path):
    response = Client().get(path)
    assert response.status_code == 302
    assert response.url.startswith("/login/")


@pytest.mark.parametrize("path", ["/", "/check/sms/", "/check/url/", "/history/", "/stats/", "/profile/"])
def test_pages_open_after_login(auth_client, path):
    assert auth_client.get(path).status_code == 200


def test_register_validation_and_success():
    client = Client()
    bad = client.post("/register/", {"username": "x", "email": "bad", "password": "short", "password2": "short"})
    assert bad.status_code == 200
    assert "Логин: 3–30".encode() in bad.content
    good = client.post(
        "/register/",
        {"username": "new_user", "email": "new@example.com", "password": PASSWORD, "password2": PASSWORD},
    )
    assert good.status_code == 302
    stored = get_user_model().objects.get(username="new_user").password
    assert stored.startswith("pbkdf2_") and PASSWORD not in stored


def test_duplicate_username_rejected(user):
    response = Client().post(
        "/register/",
        {"username": "tester", "email": "other@example.com", "password": PASSWORD, "password2": PASSWORD},
    )
    assert "логин уже занят".encode() in response.content


def test_login_lockout_after_five_failures(user):
    client = Client()
    for _ in range(5):
        client.post("/login/", {"username": "tester", "password": "wrong"})
    response = client.post("/login/", {"username": "tester", "password": PASSWORD})
    assert "Слишком много".encode() in response.content


def test_logout_destroys_session(auth_client):
    auth_client.post("/logout/")
    assert auth_client.get("/").status_code == 302


def test_api_requires_login():
    assert post_json(Client(), "/api/v1/check/sms/", {"text": "hello"}).status_code == 401


def test_csrf_is_enforced(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert post_json(client, "/api/v1/check/sms/", {"text": "hello"}).status_code == 403


@pytest.mark.parametrize("text", ["", "   ", "x" * 1001, None, 5])
def test_invalid_sms_gives_400(auth_client, text):
    response = post_json(auth_client, "/api/v1/check/sms/", {"text": text})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_binary_body_does_not_crash(auth_client):
    response = auth_client.post("/api/v1/check/sms/", data=b"\xff\xfe\x00", content_type="application/json")
    assert response.status_code == 400


def test_fraud_sms_flow(auth_client):
    response = post_json(auth_client, "/api/v1/check/sms/", {"text": FRAUD_SMS})
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "FRAUDULENT"
    assert data["language"] == "ru"
    assert data["p_sms_reliable"] is False
    assert data["urls"][0]["domain"] == "secure-bank-verify.example"
    assert data["explanation"] and data["recommendation"] and data["disclaimer"]


def test_text_is_masked_without_consent(auth_client, user):
    post_json(auth_client, "/api/v1/check/sms/", {"text": "Позвони +7 700 000 00 00, переведи 5000 тг"})
    check = Check.objects.get(user=user)
    assert check.input_text is None
    assert "700" not in check.input_masked and "5000" not in check.input_masked


def test_text_is_stored_with_consent(auth_client, user):
    UserProfile.objects.update_or_create(user=user, defaults={"store_sms_text": True})
    post_json(auth_client, "/api/v1/check/sms/", {"text": "Привет, как дела?"})
    assert Check.objects.get(user=user).input_text == "Привет, как дела?"


def test_script_is_returned_as_data_not_rendered(auth_client, user):
    post_json(auth_client, "/api/v1/check/sms/", {"text": "<script>alert(1)</script>"})
    page = auth_client.get("/history/").content.decode()
    assert "<script>alert(1)</script>" not in page


def test_sql_injection_text_is_harmless(auth_client, user):
    response = post_json(auth_client, "/api/v1/check/sms/", {"text": "' OR 1=1 --"})
    assert response.status_code == 200
    assert get_user_model().objects.filter(username="tester").exists()


def test_url_check(auth_client):
    response = post_json(auth_client, "/api/v1/check/url/", {"url": "http://192.0.2.15/account-update"})
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "URL"
    assert data["risk_score"] >= 60
    assert {row["code"] for row in data["urls"][0]["feature_table"] if row["triggered"]} >= {"has_ip"}


@pytest.mark.parametrize("url", ["", "ftp://example.com", "http://", "x" * 3000])
def test_bad_url_gives_400(auth_client, url):
    assert post_json(auth_client, "/api/v1/check/url/", {"url": url}).status_code == 400


def test_foreign_check_is_hidden(auth_client, user):
    other = get_user_model().objects.create_user("other", "other@example.com", PASSWORD)
    other_client = Client()
    other_client.force_login(other)
    check_id = post_json(other_client, "/api/v1/check/sms/", {"text": "hello there"}).json()["id"]
    assert auth_client.get(f"/checks/{check_id}/").status_code == 404
    assert auth_client.get(f"/api/v1/checks/{check_id}/").status_code == 404
    assert auth_client.delete(f"/api/v1/checks/{check_id}/").status_code == 404
    assert Check.objects.filter(pk=check_id).exists()


def test_rate_limit(auth_client):
    statuses = [post_json(auth_client, "/api/v1/check/url/", {"url": "example.com"}).status_code for _ in range(31)]
    assert statuses[:30] == [200] * 30
    assert statuses[30] == 429


def test_model_unavailable_gives_503(auth_client, monkeypatch):
    from ml import predictor

    monkeypatch.setattr(predictor, "_load_sms_model", lambda: None)
    assert post_json(auth_client, "/api/v1/check/sms/", {"text": "hello"}).status_code == 503


def test_stats_match_database(auth_client, user):
    post_json(auth_client, "/api/v1/check/sms/", {"text": FRAUD_SMS})
    post_json(auth_client, "/api/v1/check/url/", {"url": "https://www.example.com/about"})
    data = auth_client.get("/api/v1/stats/summary/").json()
    assert data["total"] == Check.objects.filter(user=user).count() == 2
    assert data["fraudulent"] == 1
    assert data["safe"] == 1
    assert len(data["per_day"]) == 30


def test_history_filter_and_pagination(auth_client, user):
    for _ in range(21):
        Check.objects.create(
            user=user, check_type="URL", input_masked="https://example.com", category="SAFE",
            risk_level="LOW", risk_score=1, recommendation="-",
        )
    page = auth_client.get("/history/?type=URL")
    assert len(page.context["page"].object_list) == 20
    assert auth_client.get("/history/?type=SMS").context["page"].paginator.count == 0
    assert auth_client.get("/history/?date_from=not-a-date").status_code == 200
