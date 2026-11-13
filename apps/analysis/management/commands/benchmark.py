"""Замер производительности для НФТ-1 и НФТ-2 (задание 18).

Запуск: python manage.py benchmark
Создаёт временного пользователя, после замера удаляет его вместе с записями.
"""
import statistics
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import override_settings

from apps.analysis.models import Check
from apps.analysis.services import analyze_sms

SMS_WITH_THREE_URLS = (
    "URGENT! Your account is blocked. Verify now: http://secure-bank-verify.example/login "
    "or www.account-update.example or bit.ly/prize-claim-test"
)
RUNS = 100
HISTORY_SIZE = 1000


class Command(BaseCommand):
    help = "Замеряет время анализа SMS (НФТ-1) и загрузки Dashboard при 1000 записях (НФТ-2)."

    def handle(self, *args, **options):
        analyze_sms(SMS_WITH_THREE_URLS)  # прогрев: модели уже загружены, кэши заполнены
        timings = []
        for _ in range(RUNS):
            started = time.perf_counter()
            analyze_sms(SMS_WITH_THREE_URLS)
            timings.append((time.perf_counter() - started) * 1000)
        p95 = sorted(timings)[int(RUNS * 0.95) - 1]
        self.stdout.write(
            f"НФТ-1: анализ SMS с 3 ссылками, {RUNS} запусков: среднее {statistics.mean(timings):.1f} мс, "
            f"95-й перцентиль {p95:.1f} мс, максимум {max(timings):.1f} мс (норма 500 мс)"
        )

        user = get_user_model().objects.create_user("benchmark_tmp", "benchmark@example.com", "Benchmark123")
        try:
            Check.objects.bulk_create(
                Check(
                    user=user, check_type="SMS", input_masked=f"Тестовая запись {i}",
                    category=["SAFE", "SUSPICIOUS", "FRAUDULENT"][i % 3], risk_level=["LOW", "MEDIUM", "HIGH"][i % 3],
                    risk_score=i % 100, recommendation="-",
                )
                for i in range(HISTORY_SIZE)
            )
            with override_settings(ALLOWED_HOSTS=["testserver"]):
                client = Client()
                client.force_login(user)
                page_times, api_times = [], []
                for _ in range(10):
                    started = time.perf_counter()
                    client.get("/")
                    page_times.append((time.perf_counter() - started) * 1000)
                    started = time.perf_counter()
                    response = client.get("/api/v1/stats/summary/?days=90")
                    api_times.append((time.perf_counter() - started) * 1000)
                assert response.json()["total"] == HISTORY_SIZE
            self.stdout.write(
                f"НФТ-2: Dashboard при {HISTORY_SIZE} записях: страница {statistics.mean(page_times):.1f} мс, "
                f"данные графиков {statistics.mean(api_times):.1f} мс (норма 2000 мс)"
            )
        finally:
            user.delete()
