"""Загрузка UCI SMS Spam Collection (задание 3).

Запуск из корня проекта: python -m ml.data.load_sms
Создаёт data/processed/sms_raw.csv и печатает сводку по набору.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = ROOT / "data" / "raw" / "SMSSpamCollection"
OUTPUT_FILE = ROOT / "data" / "processed" / "sms_raw.csv"
LABELS = {"ham": 0, "spam": 1}


def detect_encoding(path: Path = RAW_FILE) -> str:
    """Явно проверить кодировку: файл должен читаться как UTF-8, иначе latin-1."""
    try:
        path.read_bytes().decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def load_sms(path: Path = RAW_FILE) -> pd.DataFrame:
    """Вернуть DataFrame со столбцами id, text, label (0 — ham, 1 — spam)."""
    rows = []
    # Построчный разбор: в текстах встречаются кавычки, и read_csv склеивал бы строки.
    with path.open(encoding=detect_encoding(path), newline="\n") as file:
        for line in file:
            line = line.rstrip("\r\n")
            if not line:
                continue
            raw_label, text = line.split("\t", 1)
            rows.append((LABELS[raw_label], text))
    df = pd.DataFrame(rows, columns=["label", "text"])
    df.insert(0, "id", range(1, len(df) + 1))
    return df[["id", "text", "label"]]


def describe(df: pd.DataFrame) -> None:
    print(f"Строк: {len(df)}")
    print(f"Типы столбцов:\n{df.dtypes}\n")
    counts = df["label"].value_counts().sort_index()
    for label, count in counts.items():
        name = "ham (0)" if label == 0 else "spam (1)"
        print(f"{name}: {count} ({count / len(df):.2%})")
    for label in (0, 1):
        print(f"\nПримеры класса {label}:")
        for text in df.loc[df["label"] == label, "text"].head(5):
            print(f"  - {text}")


if __name__ == "__main__":
    data = load_sms()
    describe(data)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"\nСохранено: {OUTPUT_FILE.relative_to(ROOT)}")
