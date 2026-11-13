"""Данные, признаки и сохранённые модели (задания 3, 6, 7, 8, 11, 12)."""
import json

from sklearn.linear_model import LogisticRegression

from ml.data.load_sms import load_sms
from ml.features import HAND_FEATURE_NAMES, HandFeatures, build_sms_pipeline
from ml.predictor import SMS_META_PATH, URL_META_PATH, ModelRegistry, predict_sms, predict_url
from ml.url_features import MODEL_FEATURES, model_features


def test_load_sms_keeps_all_rows_and_labels():
    df = load_sms()
    assert len(df) == 5574
    assert set(df["label"]) == {0, 1}
    assert list(df.columns) == ["id", "text", "label"]


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


def test_feature_variants_for_comparison():
    words_only = build_sms_pipeline(LogisticRegression(), use_char=False, use_hand=False)
    assert [name for name, _ in words_only.named_steps["features"].transformer_list] == ["word"]


def test_model_metadata_is_complete():
    for path, keys in [
        (SMS_META_PATH, {"version", "algorithm", "params", "threshold", "metrics_test", "trained_at", "features"}),
        (URL_META_PATH, {"version", "algorithm", "params", "t1", "t2", "metrics_test", "trained_at", "features"}),
    ]:
        meta = json.loads(path.read_text(encoding="utf-8"))
        assert keys <= set(meta)
        assert meta["version"] == "1.0.0"


def test_models_are_loaded_once():
    assert ModelRegistry() is ModelRegistry()


def test_predict_sms_uses_saved_model():
    result = predict_sms("Congratulations! You won a $1000 gift card. Claim your prize now")
    assert set(result) == {"label", "probability"}
    assert result["label"] == 1
    assert predict_sms("See you at the library tomorrow")["label"] == 0


def test_predict_url_returns_probability():
    assert list(model_features("example.com")) == MODEL_FEATURES
    assert 0.0 <= predict_url(model_features("https://www.example.com")) <= 1.0
    assert predict_url(model_features("http://secure-login-verify.example")) > predict_url(model_features("example.com"))
