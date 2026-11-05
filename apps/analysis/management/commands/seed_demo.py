"""Демо-пользователь и 30 проверок из искусственных сообщений раздела 8.3.

Результаты считаются настоящим анализом; заранее заданы только тексты и даты.
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.analysis.services import analyze_sms, analyze_url, save_check

DEMO_USERNAME = "demo_user"
DEMO_PASSWORD = "DemoPass123"
DEMO_SMS = [
    "Привет! Встречаемся завтра в 18:00 у входа в библиотеку.",
    "Your order #4821 has been shipped and will arrive on Monday.",
    "Сәлем! Ертең сағат 10:00-де кездесеміз бе?",
    "Ваш код подтверждения: 4821. Никому не сообщайте этот код.",
    "Ваша карта заблокирована! Срочно подтвердите данные по ссылке: http://secure-bank-verify.example/login",
    "URGENT: Your account will be suspended in 24 hours. Verify now at http://192.0.2.15/account-update",
    "Мама, у меня проблемы, срочно переведи 50 000 на этот номер, потом всё объясню. Никому не говори.",
    "Congratulations! You won a $1000 gift card. Claim your prize: bit.ly/prize-claim-test",
    "Сотрудник службы безопасности банка: назовите код из SMS для отмены подозрительной операции.",
    "Картаңыз бұғатталды. Жедел түрде мына сілтеме арқылы растаңыз: http://bank-kz-verify.test",
    "Ваша посылка ожидает оплаты таможенного сбора 350 ₸: http://post-delivery-pay.example",
]
DEMO_URLS = [
    "https://www.example.com/about",
    "http://xn--exmple-cua.test/secure/login?verify=1",
    "https://login-account.example.com/update",
]
TOTAL_CHECKS = 30
PERIOD_DAYS = 29


class Command(BaseCommand):
    help = "Создаёт демо-пользователя и 30 проверок за последние 30 дней."

    def handle(self, *args, **options):
        user, _ = get_user_model().objects.get_or_create(
            username=DEMO_USERNAME, defaults={"email": "demo_user@example.com"}
        )
        user.set_password(DEMO_PASSWORD)
        user.save()
        UserProfile.for_user(user)
        user.checks.all().delete()

        rng = random.Random(42)
        items = [("sms", text) for text in DEMO_SMS] + [("url", url) for url in DEMO_URLS]
        for index in range(TOTAL_CHECKS):
            kind, value = items[index % len(items)]
            result = analyze_sms(value) if kind == "sms" else analyze_url(value)
            check = save_check(user, result, value)
            check.created_at = timezone.now() - timedelta(
                days=rng.randint(0, PERIOD_DAYS), minutes=rng.randint(0, 600)
            )
            check.save(update_fields=["created_at"])
        self.stdout.write(self.style.SUCCESS(f"Готово: {DEMO_USERNAME}, проверок {TOTAL_CHECKS}."))
