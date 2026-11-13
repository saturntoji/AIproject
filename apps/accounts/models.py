from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    store_sms_text = models.BooleanField(default=False)
    preferred_language = models.CharField(max_length=5, default="ru")

    @classmethod
    def for_user(cls, user) -> "UserProfile":
        return cls.objects.get_or_create(user=user)[0]
