"""Извлечение признаков URL только из строки (задел для задания 9).

Сетевых вызовов здесь нет: ссылка не открывается, DNS не запрашивается.
tldextract работает со встроенным снимком списка доменных зон (suffix_list_urls=()).
"""
import ipaddress
import math
import re
from collections import Counter
from urllib.parse import parse_qsl, urlsplit

import tldextract

from ml.preprocessing import URL_RE

MAX_URL_LENGTH = 2048
MAX_URLS_PER_SMS = 3
_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "is.gd", "cutt.ly", "ow.ly", "clck.ru", "buff.ly",
    "rebrand.ly", "tiny.cc", "shorturl.at", "rb.gy", "bl.ink", "s.id", "lnkd.in", "vk.cc", "u.to",
}
SUSPICIOUS_WORDS = (
    "login", "verify", "secure", "account", "update", "bank", "confirm", "password", "bonus",
    "free", "prize", "kaspi", "halyk", "signin", "wallet", "pay", "unlock",
)
BRAND_DOMAINS = {
    "kaspi.kz", "halykbank.kz", "jusan.kz", "bcc.kz", "forte.bank", "egov.kz", "kazpost.kz",
    "beeline.kz", "kcell.kz", "tele2.kz", "google.com", "gmail.com", "apple.com", "microsoft.com",
    "paypal.com", "amazon.com", "facebook.com", "instagram.com", "whatsapp.com", "telegram.org",
    "sberbank.ru", "netflix.com",
}
# Зоны, которые регулярно попадают в отчёты о злоупотреблениях (Spamhaus TLD, Interisle).
SUSPICIOUS_TLDS = {"xyz", "top", "click", "zip", "mov", "gq", "tk", "ml", "cf", "ga", "work", "rest", "icu"}
# Бесплатные хостинги и конструкторы сайтов, где легко разместить поддельную страницу.
FREE_HOSTING = (
    "firebaseapp.com", "web.app", "weebly.com", "wixsite.com", "000webhostapp.com", "github.io", "ipfs",
    "godaddysites.com", "vercel.app", "netlify.app", "glitch.me", "workers.dev", "repl.co", "square.site",
    "blogspot.com", "pages.dev", "herokuapp.com", "azurewebsites.net", "appspot.com", "myshopify.com",
    "sharepoint.com", "webflow.io", "r2.dev", "duckdns.org", "ngrok", "translate.goog", "wordpress.com",
    "sites.google.com", "mybluehost.me", "yolasite.com",
)
_SPECIAL_CHARS = "@~%=&_?"

FEATURE_TITLES = {
    "url_length": "Длина URL",
    "host_length": "Длина домена",
    "path_length": "Длина пути",
    "dot_count": "Число точек",
    "subdomain_count": "Число поддоменов",
    "hyphen_count": "Дефисы в домене",
    "digit_count": "Цифры в URL",
    "host_digit_ratio": "Доля цифр в домене",
    "special_char_count": "Спецсимволы (@ ~ % = & _ ?)",
    "has_ip": "IP-адрес вместо домена",
    "is_https": "Схема HTTPS",
    "nonstandard_port": "Нестандартный порт",
    "has_at": "Символ @ в URL",
    "double_slash_in_path": "Двойной // в пути",
    "is_shortener": "URL-сокращатель",
    "suspicious_word_count": "Подозрительные слова",
    "has_punycode": "Punycode (xn--)",
    "mixed_alphabets": "Смешение алфавитов в домене",
    "brand_lookalike": "Сходство с брендом",
    "host_entropy": "Энтропия домена",
    "suspicious_tld": "Подозрительная доменная зона",
    "query_param_count": "Параметры запроса",
    "free_hosting": "Бесплатный хостинг",
    "vowel_ratio": "Доля гласных в домене",
    "max_consonant_run": "Подряд согласных в домене",
    "host_token_count": "Частей в домене",
    "longest_token": "Самая длинная часть домена",
    "tld_length": "Длина доменной зоны",
    "official_domain": "Официальный домен из списка",
}
FEATURE_NAMES = list(FEATURE_TITLES)
FLAG_FEATURES = {
    "free_hosting", "official_domain", "has_ip", "is_https", "nonstandard_port", "has_at", "double_slash_in_path", "is_shortener",
    "has_punycode", "mixed_alphabets", "brand_lookalike", "suspicious_tld",
}


def extract_urls(text: str, limit: int = MAX_URLS_PER_SMS) -> list[str]:
    """Найти ссылки в тексте SMS, не более limit уникальных."""
    urls = []
    for match in URL_RE.finditer(text or ""):
        url = match.group().rstrip(".,;:!?)»")
        if url not in urls:
            urls.append(url)
        if len(urls) == limit:
            break
    return urls


def validate_url(url: str) -> tuple[str | None, str | None]:
    """Вернуть (url для разбора, None) либо (None, текст ошибки на русском)."""
    if not isinstance(url, str) or not url.strip():
        return None, "Введите ссылку."
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        return None, f"Ссылка длиннее {MAX_URL_LENGTH} символов."
    if re.search(r"[\s\x00-\x1f]", url):
        return None, "Ссылка не должна содержать пробелы и управляющие символы."
    has_scheme = re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url)
    if has_scheme and not url.lower().startswith(("http://", "https://")):
        return None, "Допустимы только схемы http и https."
    parsed = url if has_scheme else f"http://{url}"
    try:
        host = urlsplit(parsed).hostname
    except ValueError:
        return None, "Некорректный формат ссылки."
    if not host or ("." not in host and ":" not in host):
        return None, "В ссылке не найден домен."
    return parsed, None


def get_host(url: str) -> str:
    """Хост ссылки в нижнем регистре либо пустая строка, если ссылка не разбирается."""
    parsed, error = validate_url(url)
    if error:
        return ""
    return urlsplit(parsed).hostname or ""


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, 1):
        current = [i]
        for j, ch_b in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ch_a != ch_b)))
        previous = current
    return previous[-1]


def _brand_lookalike(registered: str, full_host: str) -> bool:
    """Домен похож на бренд, но им не является: опечатка или бренд внутри чужого домена."""
    if not registered or registered in BRAND_DOMAINS:
        return False
    name = registered.split(".")[0]
    for brand in BRAND_DOMAINS:
        brand_name = brand.split(".")[0]
        if len(brand_name) < 4:
            continue
        # Для коротких имён порог строже, иначе «email» считался бы похожим на «gmail».
        max_distance = 1 if len(brand_name) < 6 else 2
        if len(name) >= 4 and _levenshtein(name, brand_name) <= max_distance:
            return True
        if brand_name in full_host:
            return True
    return False


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    total = len(text)
    return -sum(n / total * math.log2(n / total) for n in Counter(text).values())


def _split_host(host: str) -> tuple[str, int, str]:
    """Вернуть (регистрируемый домен, число поддоменов, зона)."""
    ext = _extract(host)
    if ext.suffix:
        subdomains = ext.subdomain.count(".") + 1 if ext.subdomain else 0
        return f"{ext.domain}.{ext.suffix}", subdomains, ext.suffix.split(".")[-1]
    # Зоны .example и .test не входят в публичный список, разбираем по меткам.
    labels = host.split(".")
    return ".".join(labels[-2:]), max(len(labels) - 2, 0), labels[-1]


def extract_url_features(url: str) -> dict:
    """Вернуть словарь из 29 признаков с постоянным порядком ключей.

    Для некорректной ссылки возвращаются нули: функция не бросает исключений.
    """
    parsed_url, error = validate_url(url)
    if error:
        return dict.fromkeys(FEATURE_NAMES, 0)
    parts = urlsplit(parsed_url)
    host = (parts.hostname or "").lower()
    try:
        port = parts.port
    except ValueError:
        port = -1
    path = parts.path or ""
    lowered = parsed_url.lower()
    registered, subdomain_count, tld = _split_host(host)
    has_cyrillic = bool(re.search(r"[а-яёәғқңөұүһі]", host))
    has_latin = bool(re.search(r"[a-z]", host))
    host_digits = sum(ch.isdigit() for ch in host)
    is_ip = _is_ip(host)
    if is_ip:
        registered, subdomain_count, tld = "", 0, ""
    host_letters = [ch for ch in host if ch.isalpha()]
    host_tokens = [token for token in re.split(r"[.\-]", host) if token]
    # На сайте самого бренда его имя («kaspi», «halykbank») подозрительным словом не считается.
    word_text = lowered.replace(registered.split(".")[0], "") if registered in BRAND_DOMAINS else lowered
    return {
        "url_length": len(parsed_url),
        "host_length": len(host),
        "path_length": len(path),
        "dot_count": parsed_url.count("."),
        "subdomain_count": subdomain_count,
        "hyphen_count": host.count("-"),
        "digit_count": sum(ch.isdigit() for ch in parsed_url),
        "host_digit_ratio": round(host_digits / len(host), 4) if host else 0,
        "special_char_count": sum(parsed_url.count(ch) for ch in _SPECIAL_CHARS),
        "has_ip": int(is_ip),
        "is_https": int(parts.scheme == "https"),
        "nonstandard_port": int(port not in (None, 80, 443)),
        "has_at": int("@" in parsed_url),
        "double_slash_in_path": int("//" in path),
        "is_shortener": int(registered in SHORTENERS or host in SHORTENERS),
        "suspicious_word_count": sum(word in word_text for word in SUSPICIOUS_WORDS),
        "has_punycode": int("xn--" in host),
        "mixed_alphabets": int(has_cyrillic and has_latin),
        "brand_lookalike": int(_brand_lookalike(registered, host)),
        "host_entropy": round(_entropy(host), 4),
        "suspicious_tld": int(tld in SUSPICIOUS_TLDS),
        "query_param_count": len(parse_qsl(parts.query, keep_blank_values=True)),
        "free_hosting": int(any(name in host for name in FREE_HOSTING)),
        "vowel_ratio": round(sum(ch in "aeiou" for ch in host_letters) / len(host_letters), 4) if host_letters else 0,
        "max_consonant_run": max((len(run) for run in re.findall(r"[bcdfghjklmnpqrstvwxz]+", host)), default=0),
        "host_token_count": len(host_tokens),
        "longest_token": max((len(token) for token in host_tokens), default=0),
        "tld_length": len(tld),
        "official_domain": int(registered in BRAND_DOMAINS),
    }


# В наборе PhiUSIIL все безопасные адреса записаны как «https://www.домен» без пути, а у фишинговых
# путь есть в 60 % случаев. Обученная на полном адресе модель выучила бы «есть путь — значит фишинг».
# Поэтому URL-модель смотрит только на домен (и порт): адрес приводится к виду «http://домен», а признаки
# схемы и пути в модель не передаются. Они по-прежнему показываются пользователю и учитываются правилами
# риска (задание 10).
# official_domain — правило, а не признак модели: модель обучена без него.
MODEL_EXCLUDED = ("is_https", "path_length", "double_slash_in_path", "query_param_count", "has_at", "official_domain")
MODEL_FEATURES = [name for name in FEATURE_NAMES if name not in MODEL_EXCLUDED]


def canonical_url(url: str) -> str:
    """Домен ссылки без «www.» в виде «http://домен[:порт]»; для некорректной ссылки — ''."""
    parsed, error = validate_url(url)
    if error:
        return ""
    parts = urlsplit(parsed)
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    try:
        port = parts.port
    except ValueError:
        port = None
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}" + (f":{port}" if port else "")


def model_features(url: str) -> dict:
    """Признаки в том виде, в каком их получает URL-модель."""
    features = extract_url_features(canonical_url(url))
    return {name: features[name] for name in MODEL_FEATURES}


# Какие признаки считаются сработавшими на экране и какой причиной объясняются.
_FLAG_REASONS = {
    "has_ip": "Используется IP-адрес вместо доменного имени",
    "free_hosting": "Сайт размещён на бесплатном хостинге или конструкторе сайтов",
    "has_punycode": "Домен записан в Punycode: возможна маскировка под другой адрес",
    "mixed_alphabets": "В домене смешаны кириллица и латиница",
    "brand_lookalike": "Домен похож на известный бренд, но им не является",
    "has_at": "В адресе есть символ @, скрывающий настоящий домен",
    "is_shortener": "Используется сервис сокращения ссылок: настоящий адрес скрыт",
    "suspicious_tld": "Доменная зона часто используется в мошеннических рассылках",
    "nonstandard_port": "Используется нестандартный порт",
    "double_slash_in_path": "В пути адреса есть двойной //",
}


def triggered_features(features: dict) -> list[str]:
    """Коды признаков, которые выделяются на экране как сработавшие."""
    triggered = [code for code in _FLAG_REASONS if features.get(code)]
    if features.get("suspicious_word_count"):
        triggered.append("suspicious_word_count")
    if features.get("hyphen_count", 0) >= 2:
        triggered.append("hyphen_count")
    if features.get("subdomain_count", 0) >= 3:
        triggered.append("subdomain_count")
    if features.get("url_length") and not features.get("is_https"):
        triggered.append("is_https")
    return triggered


def explain_url(features: dict) -> list[str]:
    """Человекочитаемые причины для сработавших признаков."""
    reasons = [reason for code, reason in _FLAG_REASONS.items() if features.get(code)]
    if features.get("suspicious_word_count"):
        reasons.append(f"В адресе есть подозрительные слова: {features['suspicious_word_count']}")
    if features.get("hyphen_count", 0) >= 2:
        reasons.append("В домене много дефисов")
    if features.get("subdomain_count", 0) >= 3:
        reasons.append("Слишком много поддоменов")
    if features.get("url_length") and not features.get("is_https"):
        reasons.append("Соединение без HTTPS")
    return reasons
