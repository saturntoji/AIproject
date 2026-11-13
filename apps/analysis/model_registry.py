"""Синхронизация таблицы model_versions с метаданными сохранённых моделей."""
from datetime import date

from ml.predictor import SMS_META_PATH, URL_META_PATH, _read_meta


def sync_model_versions(**kwargs) -> None:
    from apps.analysis.models import ModelVersion

    for model_type, path in (("sms", SMS_META_PATH), ("url", URL_META_PATH)):
        meta = _read_meta(path)
        if not meta:
            continue
        ModelVersion.objects.filter(model_type=model_type).exclude(version=meta["version"]).update(is_active=False)
        ModelVersion.objects.update_or_create(
            model_type=model_type,
            version=meta["version"],
            defaults={
                "algorithm": meta.get("algorithm", ""),
                "metrics_json": meta.get("metrics_test", {}),
                "threshold": meta.get("threshold", meta.get("t2", 0.5)),
                "trained_at": date.fromisoformat(meta["trained_at"]) if meta.get("trained_at") else None,
                "is_active": True,
            },
        )
