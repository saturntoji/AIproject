# SMS Guard

Интеллектуальная система обнаружения мошеннических SMS и подозрительных ссылок.

**Текущее состояние:** этап 1, то есть задания 1–7 и прототип интерфейса. Прототип показывает экраны по
макетам из ТЗ: проверка, вход и база данных в нём пока не работают, данные на экранах условные.
Обученная базовая модель работает в ноутбуке и через функцию `predict_sms`.

## Запуск (Windows PowerShell)

Нужен Python 3.11 или новее.

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
.\.venv\Scripts\python.exe manage.py runserver
```

Сайт откроется на http://127.0.0.1:8000/login/. Проверка работы сервера: http://127.0.0.1:8000/api/v1/health/.

## Тесты

```bash
.\.venv\Scripts\python.exe -m pytest
```

## Воспроизведение данных и модели

Модель `ml/artifacts/sms_baseline.joblib` уже лежит в репозитории. Чтобы получить всё заново:

```bash
.\.venv\Scripts\python.exe -m ml.data.load_sms
```

```bash
.\.venv\Scripts\python.exe -m ml.data.clean_sms
```

Затем выполните ноутбуки `notebooks/01`, `02` и `03` по порядку.

## Google Colab

Проще всего использовать `notebooks/SMS_Guard_Colab.ipynb`: это задания 3–7 в одном файле, код и данные
встроены в него. В Colab выберите `Файл → Загрузить блокнот`, затем `Среда выполнения → Выполнить все`.

Отдельные ноутбуки `01`, `02` и `03` тоже работают в Colab: первая ячейка попросит загрузить архив
проекта. Архив можно собрать так:

```bash
git archive -o sms_guard.zip HEAD
```

## Структура

| Путь | Содержимое |
|---|---|
| `config/` | Настройки Django |
| `apps/` | Приложения `accounts`, `analysis`, `dashboard`: пока только страницы-макеты и health-эндпоинт |
| `ml/` | Предобработка, признаки, словарь правил, загрузка модели |
| `notebooks/` | Исследования по заданиям 5–7 |
| `data/` | Исходные и обработанные данные |
| `docs/` | Отчёты по заданиям и графики |
| `tests/` | Тесты pytest |

## Документы по заданиям

| Задание | Результат |
|---|---|
| 1 | [docs/01_domain_analysis.md](docs/01_domain_analysis.md) |
| 2 | Этот README, каркас проекта, `/api/v1/health/` |
| 3 | [docs/03_dataset_passport.md](docs/03_dataset_passport.md), `ml/data/load_sms.py`, `data/raw/custom_ru_kk.csv` |
| 4 | [docs/04_preprocessing_report.md](docs/04_preprocessing_report.md), `ml/preprocessing.py`, `tests/test_preprocessing.py` |
| 5 | `notebooks/01_eda_sms.ipynb`, `docs/figures/` |
| 6 | `notebooks/02_features_tfidf.ipynb`, `ml/features.py`, [docs/06_features_explained.md](docs/06_features_explained.md) |
| 7 | `notebooks/03_baseline_model.ipynb`, `ml/predictor.py`, `ml/artifacts/` |
