"""Подготовка набора URL (задание 10).

Запуск из корня проекта: python -m ml.data.prepare_urls
Исходный файл data/raw/url/PhiUSIIL_Phishing_URL_Dataset.csv (UCI) в репозиторий не входит из-за размера.
Результат: data/processed/url_features.parquet и docs/10_url_dataset_report.md.
"""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from ml.url_features import MODEL_FEATURES, _split_host, canonical_url, extract_url_features, validate_url

ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = ROOT / "data" / "raw" / "url" / "PhiUSIIL_Phishing_URL_Dataset.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "url_features.parquet"
REPORT_FILE = ROOT / "docs" / "10_url_dataset_report.md"
SAMPLE_SIZE = 100_000
RANDOM_STATE = 42


def load_raw(path: Path = RAW_FILE) -> pd.DataFrame:
    """В PhiUSIIL 1 — легитимный адрес, 0 — фишинг. Приводим к 0 — безопасный, 1 — фишинг."""
    df = pd.read_csv(path, usecols=["URL", "label"], encoding="utf-8")
    return pd.DataFrame({"url": df["URL"].astype(str).str.strip(), "label": 1 - df["label"]})


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    steps = [("Исходных записей", len(df))]
    df = df[df["url"] != ""]
    df = df[df["url"].map(lambda u: validate_url(u)[1] is None)]
    steps.append(("После удаления пустых и некорректных", len(df)))

    df = df.assign(canonical=df["url"].map(canonical_url))
    # Модель видит только домен, поэтому одинаковые домены — дубликаты. Домены с разными метками
    # (например, хостинг, где есть и обычные, и фишинговые сайты) противоречивы и удаляются.
    labels_per_host = df.groupby("canonical")["label"].nunique()
    conflicting = labels_per_host[labels_per_host > 1].index
    steps.append(("Удалено записей с противоречивой меткой домена", int(df["canonical"].isin(conflicting).sum())))
    df = df[~df["canonical"].isin(conflicting)]
    df = df.drop_duplicates("canonical")
    steps.append(("После удаления дубликатов доменов", len(df)))
    return df, steps


def stratified_sample(df: pd.DataFrame, size: int = SAMPLE_SIZE) -> pd.DataFrame:
    if len(df) <= size:
        return df
    sample, _ = train_test_split(df, train_size=size, stratify=df["label"], random_state=RANDOM_STATE)
    return sample


def group_split(df: pd.DataFrame) -> pd.Series:
    """70/15/15 по группам регистрируемого домена: один домен не попадает в разные выборки."""
    groups = df["domain_group"].to_numpy()
    first = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=RANDOM_STATE)
    train_idx, rest_idx = next(first.split(df, groups=groups))
    rest = df.iloc[rest_idx]
    second = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=RANDOM_STATE)
    val_idx, test_idx = next(second.split(rest, groups=rest["domain_group"].to_numpy()))
    split = pd.Series("train", index=df.index)
    split.iloc[rest_idx[val_idx]] = "val"
    split.iloc[rest_idx[test_idx]] = "test"
    return split


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = [extract_url_features(url) for url in df["canonical"]]
    features = pd.DataFrame(rows, index=df.index)[MODEL_FEATURES]
    return pd.concat([df[["url", "canonical", "domain_group", "label", "split"]], features], axis=1)


def write_report(steps, data: pd.DataFrame) -> None:
    lines = [
        "# Отчёт о подготовке набора URL (задание 10)",
        "",
        "Файл создан скриптом `python -m ml.data.prepare_urls`.",
        "",
        "| Шаг | Записей |",
        "|---|---:|",
        *[f"| {name} | {value} |" for name, value in steps],
        "",
        "| Выборка | Записей | Доля фишинга | Доменов |",
        "|---|---:|---:|---:|",
    ]
    for name in ("train", "val", "test"):
        part = data[data["split"] == name]
        lines.append(f"| {name} | {len(part)} | {part['label'].mean():.2%} | {part['domain_group'].nunique()} |")
    overlap = set(data.loc[data.split == "train", "domain_group"]) & set(data.loc[data.split == "test", "domain_group"])
    lines += ["", f"Общих регистрируемых доменов у train и test: {len(overlap)}.", ""]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main() -> pd.DataFrame:
    raw = load_raw()
    cleaned, steps = clean(raw)
    sample = stratified_sample(cleaned)
    steps.append(("Стратифицированная подвыборка", len(sample)))
    sample = sample.assign(domain_group=sample["canonical"].map(lambda u: _split_host(u[7:].split(":")[0])[0]))
    sample = sample.assign(split=group_split(sample))
    data = build_features(sample)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(OUTPUT_FILE, index=False)
    write_report(steps, data)
    return data


if __name__ == "__main__":
    result = main()
    print(result["split"].value_counts().to_dict(), result["label"].mean().round(4))
    print(f"Сохранено: {OUTPUT_FILE.relative_to(ROOT)}")
