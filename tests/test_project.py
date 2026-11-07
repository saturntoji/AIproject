import pytest
from django.test import Client
from sklearn.linear_model import LogisticRegression

from ml.data.load_sms import load_sms
from ml.features import HAND_FEATURE_NAMES, HandFeatures, build_sms_pipeline
from ml.predictor import predict_sms
from ml.rules import RULE_GROUPS, find_rule_groups


def test_health():
    response = Client().get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/login/", "/", "/check/sms/", "/check/url/", "/history/"])
def test_mockup_pages_open(path):
    assert Client().get(path).status_code == 200


def test_mockup_pages_have_no_forms_that_send_data():
    for path in ("/check/sms/", "/check/url/", "/history/"):
        assert b"<form" not in Client().get(path).content


def test_load_sms_keeps_all_rows_and_labels():
    df = load_sms()
    assert len(df) == 5574
    assert set(df["label"]) == {0, 1}
    assert list(df.columns) == ["id", "text", "label"]


def test_rule_groups():
    assert len(RULE_GROUPS) >= 6
    assert "CODE_REQUEST" in find_rule_groups("Назовите код из SMS для отмены операции")
    assert "CODE_REQUEST" not in find_rule_groups("Ваш код подтверждения: 4821. Никому не сообщайте этот код.")


def test_hand_features_are_scaled_by_train_values():
    features = HandFeatures().fit(["short text", "A much longer message with money $5 and http://a.example"])
    matrix = features.transform(["FREE PRIZE!!! " * 20])
    assert matrix.shape == (1, len(HAND_FEATURE_NAMES))
    assert matrix.max() <= 1.0


def test_pipeline_trains_on_small_sample():
    pipeline = build_sms_pipeline(LogisticRegression(max_iter=200))
    texts = ["win free prize now", "free prize call now", "see you at home", "see you at school"]
    pipeline.fit(texts, [1, 1, 0, 0])
    assert pipeline.predict_proba(["win free prize"]).shape == (1, 2)


def test_predict_sms_uses_saved_model():
    result = predict_sms("Congratulations! You won a $1000 gift card. Claim your prize now")
    assert set(result) == {"label", "probability"}
    assert result["label"] == 1
    assert predict_sms("See you at the library tomorrow")["label"] == 0
