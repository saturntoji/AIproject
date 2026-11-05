"""Загрузка сохранённой SMS-модели и предсказание (задание 7).

Модель загружается один раз за жизнь процесса.
"""
import json
import logging
from functools import lru_cache
from pathlib import Path

import joblib

logger = logging.getLogger(__name__)
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
SMS_MODEL_PATH = ARTIFACTS / "sms_baseline.joblib"
SMS_META_PATH = ARTIFACTS / "sms_baseline_meta.json"


class ModelUnavailable(Exception):
    """Файл модели отсутствует или не читается."""


@lru_cache(maxsize=1)
def _load_sms_model():
    if not SMS_MODEL_PATH.exists():
        logger.error("Файл модели не найден: %s. Анализ текста недоступен.", SMS_MODEL_PATH.name)
        return None
    try:
        model = joblib.load(SMS_MODEL_PATH)
    except Exception:
        logger.exception("Не удалось загрузить модель %s", SMS_MODEL_PATH.name)
        return None
    logger.info("SMS-модель загружена: %s", SMS_MODEL_PATH.name)
    return model


@lru_cache(maxsize=1)
def load_sms_meta() -> dict:
    if not SMS_META_PATH.exists():
        return {}
    return json.loads(SMS_META_PATH.read_text(encoding="utf-8"))


def is_sms_model_ready() -> bool:
    return _load_sms_model() is not None


def predict_sms(text: str) -> dict:
    """Вернуть {'label': 0|1, 'probability': P(мошенничество)} для одного сообщения."""
    model = _load_sms_model()
    if model is None:
        raise ModelUnavailable("SMS-модель не загружена")
    probability = float(model.predict_proba([text])[0, 1])
    threshold = load_sms_meta().get("threshold", 0.5)
    return {"label": int(probability >= threshold), "probability": round(probability, 4)}
