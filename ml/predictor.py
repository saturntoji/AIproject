"""Загрузка моделей и предсказание (задания 7 и 12).

ModelRegistry — синглтон: SMS- и URL-модель загружаются один раз за жизнь процесса.
Если файла модели нет, приложение всё равно стартует, а проверка сообщает о недоступности.
"""
import json
import logging
import threading
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
SMS_MODEL_PATH = ARTIFACTS / "sms_model.joblib"
SMS_META_PATH = ARTIFACTS / "sms_model_meta.json"
URL_MODEL_PATH = ARTIFACTS / "url_model.joblib"
URL_META_PATH = ARTIFACTS / "url_model_meta.json"


class ModelUnavailable(Exception):
    """Файл модели отсутствует или не читается."""


def _read_meta(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _load(path: Path):
    if not path.exists():
        logger.error("Файл модели не найден: %s. Этот вид анализа недоступен.", path.name)
        return None
    try:
        model = joblib.load(path)
    except Exception:
        logger.exception("Не удалось загрузить модель %s", path.name)
        return None
    logger.info("Модель загружена: %s", path.name)
    return model


class ModelRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance.sms_model = _load(SMS_MODEL_PATH)
                instance.sms_meta = _read_meta(SMS_META_PATH)
                instance.url_model = _load(URL_MODEL_PATH)
                instance.url_meta = _read_meta(URL_META_PATH)
                cls._instance = instance
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Сбросить загруженные модели (используется в тестах)."""
        with cls._lock:
            cls._instance = None


def get_registry() -> ModelRegistry:
    return ModelRegistry()


def is_sms_model_ready() -> bool:
    return get_registry().sms_model is not None


def is_url_model_ready() -> bool:
    return get_registry().url_model is not None


def load_sms_meta() -> dict:
    return get_registry().sms_meta


def load_url_meta() -> dict:
    return get_registry().url_meta


def predict_sms(text: str) -> dict:
    """Вернуть {'label': 0|1, 'probability': P(мошенничество)} для одного сообщения."""
    registry = get_registry()
    if registry.sms_model is None:
        raise ModelUnavailable("SMS-модель не загружена")
    probability = float(registry.sms_model.predict_proba([text])[0, 1])
    threshold = registry.sms_meta.get("threshold", 0.5)
    return {"label": int(probability >= threshold), "probability": round(probability, 4)}


def predict_url(model_features: dict) -> float:
    """Вероятность опасности ссылки по признакам из ml.url_features.model_features."""
    registry = get_registry()
    if registry.url_model is None:
        raise ModelUnavailable("URL-модель не загружена")
    names = registry.url_meta["features"]
    row = np.array([[model_features[name] for name in names]], dtype=float)
    return round(float(registry.url_model.predict_proba(row)[0, 1]), 4)
