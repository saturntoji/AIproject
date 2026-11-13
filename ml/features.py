"""Признаки SMS для ML-моделей (задание 6).

На вход pipeline подаётся исходный текст: доля заглавных букв считается по нему,
а TF-IDF получает текст после normalize_sms через параметр preprocessor.
Все шаги обучаются только на train, потому что находятся внутри Pipeline.
"""
import numpy as np
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline

from ml.preprocessing import normalize_sms, remove_stopwords
from ml.rules import find_rule_groups

# <url>, <money> и другие токены, слова от 2 символов, а также ! и ? как отдельные токены.
WORD_TOKEN_PATTERN = r"<\w+>|\w\w+|[!?]"

HAND_FEATURE_NAMES = [
    "length",
    "upper_ratio",
    "exclamation_count",
    "has_url",
    "has_money",
    "has_phone",
    "rule_group_count",
]


def compute_hand_features(text: str) -> list[float]:
    letters = [ch for ch in text if ch.isalpha()]
    upper_ratio = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0.0
    clean = normalize_sms(text)
    return [
        float(len(text)),
        upper_ratio,
        float(text.count("!")),
        float("<url>" in clean),
        float("<money>" in clean),
        float("<phone>" in clean),
        float(len(find_rule_groups(text))),
    ]


class HandFeatures(BaseEstimator, TransformerMixin):
    """Ручные признаки, приведённые к [0, 1] по максимумам обучающей выборки.

    Значения неотрицательны, поэтому признаки подходят и для Multinomial Naive Bayes.
    """

    def fit(self, X, y=None):
        values = np.array([compute_hand_features(t) for t in X])
        self.max_ = np.maximum(values.max(axis=0), 1.0)
        return self

    def transform(self, X):
        values = np.array([compute_hand_features(t) for t in X])
        return sparse.csr_matrix(np.clip(values / self.max_, 0.0, 1.0))

    def get_feature_names_out(self, input_features=None):
        return np.array(HAND_FEATURE_NAMES, dtype=object)


def normalize_without_stopwords(text: str) -> str:
    """Вариант предобработки для сравнения в задании 8."""
    return remove_stopwords(normalize_sms(text))


def build_word_tfidf(remove_stop: bool = False) -> TfidfVectorizer:
    return TfidfVectorizer(
        preprocessor=normalize_without_stopwords if remove_stop else normalize_sms,
        token_pattern=WORD_TOKEN_PATTERN,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )


def build_char_tfidf() -> TfidfVectorizer:
    return TfidfVectorizer(
        preprocessor=normalize_sms,
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )


def build_feature_union(use_char: bool = True, remove_stop: bool = False, use_hand: bool = True) -> FeatureUnion:
    """Набор признаков. Параметры нужны для сравнения вариантов в задании 8."""
    parts = [("word", build_word_tfidf(remove_stop))]
    if use_char:
        parts.append(("char", build_char_tfidf()))
    if use_hand:
        parts.append(("hand", HandFeatures()))
    return FeatureUnion(parts)


def build_sms_pipeline(classifier, **feature_options) -> Pipeline:
    """Pipeline «признаки + классификатор»: сохраняется в joblib целиком."""
    return Pipeline([("features", build_feature_union(**feature_options)), ("clf", classifier)])
