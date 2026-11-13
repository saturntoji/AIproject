"""Определение языка правилом по алфавиту (допустимая альтернатива из раздела 3.2)."""
import unicodedata

KAZAKH_LETTERS = set("әғқңөұүһі")
TRAINED_LANGUAGES = {"en"}


def detect_language(text: str) -> str:
    """Вернуть 'ru', 'kk', 'en' или 'other'."""
    letters = [ch for ch in (text or "").lower() if ch.isalpha()]
    if not letters:
        return "other"
    if any(ch in KAZAKH_LETTERS for ch in letters):
        return "kk"
    cyrillic = sum("а" <= ch <= "я" or ch == "ё" for ch in letters)
    latin = sum("a" <= ch <= "z" for ch in letters)
    if cyrillic / len(letters) >= 0.5:
        return "ru"
    if latin / len(letters) >= 0.9 and not _has_accented_latin(letters):
        return "en"
    return "other"


def _has_accented_latin(letters: list[str]) -> bool:
    return any("LATIN" in unicodedata.name(ch, "") and not ch.isascii() for ch in letters)
