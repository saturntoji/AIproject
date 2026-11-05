"""Очистка набора SMS (задание 4).

Запуск из корня проекта: python -m ml.data.clean_sms
Создаёт data/processed/sms_clean.csv и docs/04_preprocessing_report.md.
"""
from pathlib import Path

import pandas as pd

from ml.preprocessing import normalize_sms

ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = ROOT / "data" / "processed" / "sms_raw.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "sms_clean.csv"
REPORT_FILE = ROOT / "docs" / "04_preprocessing_report.md"
TOKENS = ["<url>", "<email>", "<phone>", "<money>", "<num>"]


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]], dict[int, int]]:
    """Вернуть очищенный набор, строки отчёта и число удалённых дубликатов по классам."""
    df = df.rename(columns={"text": "text_raw"}).copy()
    df["text_raw"] = df["text_raw"].fillna("")
    df["text_clean"] = df["text_raw"].map(normalize_sms)
    steps = [("Исходных записей", len(df))]

    steps.append(("Изменено нормализацией (регистр, токены, пробелы)",
                  int((df["text_raw"] != df["text_clean"]).sum())))
    for token in TOKENS:
        steps.append((f"Содержат токен {token}", int(df["text_clean"].str.contains(token, regex=False).sum())))

    empty = df["text_clean"] == ""
    steps.append(("Удалено пустых после очистки", int(empty.sum())))
    df = df[~empty]

    duplicated = df.duplicated("text_clean", keep="first")
    removed = df.loc[duplicated, "label"].value_counts().to_dict()
    removed = {label: int(removed.get(label, 0)) for label in (0, 1)}
    steps.append(("Удалено дубликатов по text_clean, ham (0)", removed[0]))
    steps.append(("Удалено дубликатов по text_clean, spam (1)", removed[1]))
    df = df[~duplicated]

    steps.append(("Осталось записей", len(df)))
    return df[["id", "text_raw", "text_clean", "label"]], steps, removed


def write_report(steps: list[tuple[str, int]], clean: pd.DataFrame) -> None:
    counts = clean["label"].value_counts().sort_index()
    lines = [
        "# Отчёт о предобработке SMS (задание 4)",
        "",
        "Файл создан скриптом `python -m ml.data.clean_sms`.",
        "",
        "| Шаг | Записей |",
        "|---|---:|",
        *[f"| {name} | {value} |" for name, value in steps],
        "",
        "## Баланс классов после очистки",
        "",
        "| Класс | Записей | Доля |",
        "|---|---:|---:|",
        f"| ham (0) | {counts[0]} | {counts[0] / len(clean):.2%} |",
        f"| spam (1) | {counts[1]} | {counts[1] / len(clean):.2%} |",
        "",
        "Стоп-слова на этом шаге не удаляются: функция `remove_stopwords` оставлена как опция,",
        "её эффект проверяется в задании 8.",
        "",
    ]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    cleaned, report_steps, _ = clean_dataframe(pd.read_csv(INPUT_FILE, encoding="utf-8"))
    cleaned.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    write_report(report_steps, cleaned)
    for step_name, step_value in report_steps:
        print(f"{step_name}: {step_value}")
    print(f"Сохранено: {OUTPUT_FILE.relative_to(ROOT)}, {REPORT_FILE.relative_to(ROOT)}")
