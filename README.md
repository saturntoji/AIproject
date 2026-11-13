# SMS Guard

Интеллектуальная система обнаружения мошеннических SMS и подозрительных ссылок.
Пользователь вводит текст SMS или ссылку, две обученные модели и словарь правил оценивают угрозу,
а система выставляет Risk Score от 0 до 100 и объясняет результат.
Оценка носит вероятностный характер и не гарантирует безопасность.

## Запуск (Windows PowerShell)

Нужен Python 3.11 или новее. Команды выполняются из папки проекта.

```bash
py -3 -m venv .venv
```

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```bash
copy .env.example .env
```

```bash
.\.venv\Scripts\python.exe manage.py migrate
```

```bash
.\.venv\Scripts\python.exe manage.py seed_demo
```

```bash
.\.venv\Scripts\python.exe manage.py runserver
```

Сайт: http://127.0.0.1:8000/. Локальные демо-входы:

| Роль | Логин | Пароль |
|---|---|---|
| Пользователь (30 проверок) | `demo_user` | `DemoPass123` |
| Администратор (статистика по всем) | `admin_demo` | `AdminPass123` |

### Демо-сборка с DEBUG=False

В `.env` задайте `DJANGO_DEBUG=False` и длинный случайный `DJANGO_SECRET_KEY`, затем:

```bash
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

Статика раздаётся через WhiteNoise. При работе по HTTPS включите `DJANGO_HTTPS=True`: тогда cookie получат флаг `Secure`.

## Тесты и замеры

```bash
.\.venv\Scripts\python.exe -m pytest --cov=ml
```

```bash
.\.venv\Scripts\python.exe manage.py benchmark
```

## Воспроизведение данных и моделей

Модели уже лежат в `ml/artifacts/`. Чтобы получить всё заново:

1. `python -m ml.data.load_sms`, затем `python -m ml.data.clean_sms` — набор SMS.
2. Ноутбуки `notebooks/01`–`04` по порядку — анализ, признаки, базовая и итоговая SMS-модель.
3. Скачать [PhiUSIIL Phishing URL Dataset](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset),
   положить `PhiUSIIL_Phishing_URL_Dataset.csv` в `data/raw/url/` (в репозиторий не входит из-за размера 57 МБ),
   выполнить `python -m ml.data.prepare_urls`.
4. Ноутбук `notebooks/05_url_models.ipynb` — URL-модель, затем `06_risk_calibration.ipynb` — калибровка риска.

Ноутбук `notebooks/SMS_Guard_Colab.ipynb` повторяет задания 3–7 одним файлом для Google Colab.

## REST API

Все запросы, кроме `health`, требуют входа (сессия). POST-запросы требуют заголовок `X-CSRFToken`.
Ошибки возвращаются в едином формате: `{"error": {"code": "VALIDATION_ERROR", "message": "…"}}`.

| Метод | Адрес | Назначение | Ответ |
|---|---|---|---|
| POST | `/api/v1/auth/register/` | Регистрация `{username, email, password}` | 201 / 400 |
| POST | `/api/v1/auth/login/` | Вход `{username, password}` | 200 / 401 / 429 |
| POST | `/api/v1/auth/logout/` | Выход | 204 |
| POST | `/api/v1/check/sms/` | Анализ SMS `{text}` | 200 / 400 / 429 / 503 |
| POST | `/api/v1/check/url/` | Анализ URL `{url}` | 200 / 400 / 429 / 503 |
| GET | `/api/v1/checks/` | История: `date_from`, `date_to`, `type`, `category`, `risk_level`, `page` | 200 |
| GET | `/api/v1/checks/{id}/` | Подробный результат | 200 / 404 |
| DELETE | `/api/v1/checks/{id}/` | Удаление своей записи | 204 / 404 |
| GET | `/api/v1/stats/summary/?days=30` | Данные Dashboard (7 / 30 / 90 дней) | 200 |
| GET | `/api/v1/health/` | Статус приложения и моделей | 200 |

Пример с `curl` (Git Bash): сначала получаем CSRF-cookie со страницы входа, затем входим и проверяем SMS.

```bash
curl -s -c cookies.txt http://127.0.0.1:8000/login/ > /dev/null
```

```bash
curl -s -b cookies.txt -c cookies.txt -H "Content-Type: application/json" -H "X-CSRFToken: $(grep csrftoken cookies.txt | cut -f7)" -H "Referer: http://127.0.0.1:8000/" -d '{"username": "demo_user", "password": "DemoPass123"}' http://127.0.0.1:8000/api/v1/auth/login/
```

```bash
curl -s -b cookies.txt -H "Content-Type: application/json" -H "X-CSRFToken: $(grep csrftoken cookies.txt | cut -f7)" -H "Referer: http://127.0.0.1:8000/" -d '{"text": "URGENT: Your account will be suspended. Verify now at http://192.0.2.15/account-update"}' http://127.0.0.1:8000/api/v1/check/sms/
```

## Структура проекта

| Путь | Содержимое |
|---|---|
| `config/` | Настройки Django, маршруты, логирование |
| `apps/accounts/` | Регистрация, вход, профиль, API учётных записей |
| `apps/analysis/` | Сервис анализа, API проверок, модели БД, история, команды `seed_demo` и `benchmark` |
| `apps/dashboard/` | Dashboard, статистика, агрегаты для графиков |
| `ml/preprocessing.py` | Нормализация SMS |
| `ml/features.py` | Признаки текста и Pipeline |
| `ml/rules.py` | Словарь социальной инженерии (8 групп, ru / kk / en) |
| `ml/language.py` | Определение языка |
| `ml/url_features.py` | 29 признаков URL без сетевых запросов |
| `ml/risk.py`, `risk_config.yaml` | Расчёт Risk Score, веса и пороги |
| `ml/predictor.py` | Загрузка обеих моделей один раз (ModelRegistry) |
| `ml/data/` | Загрузка, очистка, разбиение SMS и подготовка набора URL |
| `ml/artifacts/` | Обученные модели и их метаданные |
| `notebooks/` | Исследования по заданиям 5–13 |
| `data/` | Исходные и обработанные данные |
| `docs/` | Отчёты по заданиям, диаграммы, графики |
| `templates/`, `static/` | Страницы, стили, JavaScript |
| `tests/` | Тесты pytest |

## Документы по заданиям

| Задание | Результат |
|---|---|
| 1 | [docs/01_domain_analysis.md](docs/01_domain_analysis.md), `docs/figures/use_case.png` |
| 2 | Этот README, каркас проекта, `/api/v1/health/` |
| 3 | [docs/03_dataset_passport.md](docs/03_dataset_passport.md), `ml/data/load_sms.py`, `data/raw/custom_ru_kk.csv` |
| 4 | [docs/04_preprocessing_report.md](docs/04_preprocessing_report.md), `ml/preprocessing.py` |
| 5 | `notebooks/01_eda_sms.ipynb`, `docs/figures/eda_*.png` |
| 6 | `notebooks/02_features_tfidf.ipynb`, `ml/features.py`, [docs/06_features_explained.md](docs/06_features_explained.md) |
| 7 | `notebooks/03_baseline_model.ipynb`, `ml/artifacts/sms_baseline.joblib` |
| 8 | `notebooks/04_sms_models.ipynb`, `ml/artifacts/sms_model.joblib` и `sms_model_meta.json` |
| 9 | `ml/url_features.py`, `tests/test_url_features.py` |
| 10 | `ml/data/prepare_urls.py`, [docs/10_url_dataset_report.md](docs/10_url_dataset_report.md), `data/processed/url_features.parquet` |
| 11 | `notebooks/05_url_models.ipynb`, `ml/artifacts/url_model.joblib` и `url_model_meta.json` |
| 12 | `ml/predictor.py`, `apps/analysis/services.py`, `tests/test_services.py` |
| 13 | `ml/risk.py`, `risk_config.yaml`, `notebooks/06_risk_calibration.ipynb`, `tests/test_risk.py` |
| 14 | `apps/analysis/api.py`, `apps/accounts/api.py`, раздел «REST API» выше |
| 15 | `templates/`, `static/js/` |
| 16 | `apps/*/models.py`, [docs/figures/er_diagram.png](docs/figures/er_diagram.png), `docs/diagrams/er.puml` |
| 17 | `apps/dashboard/`, `static/js/dashboard.js` |
| 18 | [docs/18_testing_report.md](docs/18_testing_report.md) |

## База данных

Используется SQLite: это допустимая альтернатива из раздела 3.2 ТЗ. Для локальной демонстрации
отдельный сервер PostgreSQL не нужен, а запуск и перенос проекта становятся проще.
