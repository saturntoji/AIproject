"""Очистка и нормализация SMS (задание 4).

normalize_sms — единая чистая функция: её вызывают и ноутбуки, и веб-приложение,
поэтому обучение и работа сайта видят текст одинаково.
"""
import re
import unicodedata

# Схема или www., либо голый домен с известной зоной (bit.ly/abc), либо голый IPv4.
# Зоны перечислены явно: в SMS часто нет пробела после точки («ok.i»), и без списка
# такие склейки принимались бы за ссылки.
_BARE_TLDS = (
    "com|net|org|info|biz|edu|gov|co|io|me|ly|gd|gl|cc|to|su|ru|kz|uk|us|de|fr|cn"
    "|xyz|top|click|zip|site|online|shop|club|link|live|example|test|invalid|рф|қаз"
)
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+"
    rf"|(?<![\w@.-])(?:[\w-]+\.)+(?:{_BARE_TLDS})(?![\w.-]*\w)(?:[/?#:][^\s<>\"']*)?"
    r"|(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?/[^\s<>\"']*",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)

_NUMBER = r"\d[\d\s.,]*\d|\d"
_CURRENCY_BEFORE = r"[$£€₸₽]"
_CURRENCY_AFTER = (
    r"[$£€₸₽]|руб(?:\.|л[а-яё]*)?|тг\.?|тенге|теңге|usd|kzt|rub|eur|gbp"
    r"|pounds?|dollars?|p(?=\b|/)|pence"
)
MONEY_RE = re.compile(
    rf"{_CURRENCY_BEFORE}\s?(?:{_NUMBER})"
    rf"|(?<![\w.])(?:{_NUMBER})\s?(?:{_CURRENCY_AFTER})(?!\w)",
    re.IGNORECASE,
)
_PHONE_CANDIDATE_RE = re.compile(r"(?<![\w.])\+?\d[\d\s().-]{7,}\d(?![\w])")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
_SPACES_RE = re.compile(r"\s+")
_PRESSURE_RE = re.compile(r"[!?]")
_MIN_PHONE_DIGITS, _MAX_PHONE_DIGITS = 10, 15


def _replace_phone(match: re.Match) -> str:
    digits = sum(ch.isdigit() for ch in match.group())
    if _MIN_PHONE_DIGITS <= digits <= _MAX_PHONE_DIGITS:
        return " <phone> "
    return match.group()


def _strip_control_chars(text: str) -> str:
    # Категория C — управляющие символы; перевод строки и табуляцию превращаем в пробел.
    return "".join(
        " " if ch.isspace() else ch
        for ch in text
        if ch.isspace() or not unicodedata.category(ch).startswith("C")
    )


def normalize_sms(text: str) -> str:
    """Вернуть нормализованный текст SMS. Для пустого или нестрокового ввода — ''."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _strip_control_chars(text).lower()
    # Порядок важен: сначала длинные сущности, иначе <num> съест части адресов и сумм.
    text = URL_RE.sub(" <url> ", text)
    text = EMAIL_RE.sub(" <email> ", text)
    text = MONEY_RE.sub(" <money> ", text)
    text = _PHONE_CANDIDATE_RE.sub(_replace_phone, text)
    text = NUM_RE.sub(" <num> ", text)
    # ! и ? — отдельные токены: это признаки давления на получателя.
    text = _PRESSURE_RE.sub(lambda m: f" {m.group()} ", text)
    return _SPACES_RE.sub(" ", text).strip()


def remove_stopwords(text: str) -> str:
    """Опция для сравнения в задании 8: убрать английские стоп-слова NLTK."""
    return " ".join(w for w in text.split() if w not in _english_stopwords())


_stopwords_cache: frozenset[str] | None = None


def _english_stopwords() -> frozenset[str]:
    global _stopwords_cache
    if _stopwords_cache is None:
        import nltk
        from nltk.corpus import stopwords

        try:
            words = stopwords.words("english")
        except LookupError:
            nltk.download("stopwords", quiet=True)
            words = stopwords.words("english")
        _stopwords_cache = frozenset(words)
    return _stopwords_cache
