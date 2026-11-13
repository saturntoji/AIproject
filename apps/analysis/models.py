from django.conf import settings
from django.db import models
from django.utils import timezone


class Check(models.Model):
    TYPE_SMS, TYPE_URL = "SMS", "URL"
    TYPES = [(TYPE_SMS, "SMS"), (TYPE_URL, "URL")]
    CATEGORIES = [
        ("SAFE", "Безопасное"),
        ("SUSPICIOUS", "Подозрительное"),
        ("FRAUDULENT", "Мошенническое"),
        ("DANGEROUS", "Опасная"),
    ]
    LEVELS = [("LOW", "Низкий"), ("MEDIUM", "Средний"), ("HIGH", "Высокий")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checks")
    check_type = models.CharField(max_length=3, choices=TYPES)
    input_text = models.TextField(null=True, blank=True)
    input_masked = models.TextField()
    language = models.CharField(max_length=5, default="other")
    category = models.CharField(max_length=10, choices=CATEGORIES)
    risk_level = models.CharField(max_length=6, choices=LEVELS)
    risk_score = models.PositiveSmallIntegerField()
    p_sms = models.FloatField(null=True, blank=True)
    explanation = models.JSONField(default=list)
    recommendation = models.TextField()
    sms_model_version = models.CharField(max_length=30, blank=True)
    url_model_version = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["category"]),
        ]


class UrlResult(models.Model):
    check_ref = models.ForeignKey(Check, on_delete=models.CASCADE, related_name="url_results", db_column="check_id")
    url = models.TextField()
    domain = models.CharField(max_length=255)
    p_url = models.FloatField()
    category = models.CharField(max_length=10)
    features_json = models.JSONField(default=dict)


class DetectedFeature(models.Model):
    check_ref = models.ForeignKey(
        Check, on_delete=models.CASCADE, related_name="detected_features", db_column="check_id"
    )
    code = models.CharField(max_length=30)
    title = models.CharField(max_length=100)
    weight = models.FloatField(default=1.0)


class ModelVersion(models.Model):
    """Справочник версий моделей; заполняется из метаданных в ml/artifacts после migrate."""

    TYPES = [("sms", "SMS"), ("url", "URL")]

    model_type = models.CharField(max_length=3, choices=TYPES)
    version = models.CharField(max_length=30)
    algorithm = models.CharField(max_length=100)
    metrics_json = models.JSONField(default=dict)
    threshold = models.FloatField()
    trained_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["model_type", "version"], name="unique_model_version")]
