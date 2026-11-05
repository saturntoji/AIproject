"""Стратифицированное разбиение 70/15/15 (задание 6). Индексы — столбец id из sms_clean.csv."""
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
CLEAN_FILE = ROOT / "data" / "processed" / "sms_clean.csv"
SPLIT_FILE = ROOT / "data" / "processed" / "sms_split.json"
RANDOM_STATE = 42


def make_split(df: pd.DataFrame) -> dict[str, list[int]]:
    train, rest = train_test_split(df, test_size=0.30, stratify=df["label"], random_state=RANDOM_STATE)
    val, test = train_test_split(rest, test_size=0.50, stratify=rest["label"], random_state=RANDOM_STATE)
    return {"train": sorted(train["id"]), "val": sorted(val["id"]), "test": sorted(test["id"])}


def save_split(split: dict[str, list[int]]) -> None:
    payload = {name: [int(i) for i in ids] for name, ids in split.items()}
    SPLIT_FILE.write_text(json.dumps(payload), encoding="utf-8")


def load_datasets() -> dict[str, pd.DataFrame]:
    """Вернуть выборки train / val / test по сохранённым индексам."""
    df = pd.read_csv(CLEAN_FILE, encoding="utf-8").set_index("id", drop=False)
    split = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))
    return {name: df.loc[ids] for name, ids in split.items()}
