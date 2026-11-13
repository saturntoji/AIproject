from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AnalysisConfig(AppConfig):
    name = "apps.analysis"

    def ready(self):
        # Модели загружаются один раз при старте; без файлов приложение всё равно запускается.
        from apps.analysis.model_registry import sync_model_versions
        from ml.predictor import get_registry

        get_registry()
        post_migrate.connect(sync_model_versions, sender=self)
