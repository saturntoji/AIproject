from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    name = "apps.analysis"

    def ready(self):
        # Модель загружается один раз при старте; без файла приложение всё равно запускается.
        from ml.predictor import is_sms_model_ready

        is_sms_model_ready()
