"""Словарь признаков социальной инженерии: 8 групп, ru / kk / en.

Выражения — начала слов: окончание может быть любым («заблокирован» найдёт и
«заблокирована»). Левая граница слова обязательна, чтобы «win» не срабатывал в «twin».
Поиск идёт по исходному тексту, а не по нормализованному: в нормализованном
«24 часа» уже превратилось бы в «<num> часа».
"""
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleGroup:
    code: str
    title: str
    reason: str
    phrases: tuple[str, ...]


RULE_GROUPS = (
    RuleGroup(
        "URGENCY", "Срочность", "Сообщение требует срочного действия",
        (
            # ru
            "срочно", "немедленно", "в течение 24 час", "в течение часа", "сегодня последний",
            "последний день", "последнее предупреждение", "осталось всего", "не откладывайте",
            "прямо сейчас", "успейте", "как можно скорее",
            # kk
            "шұғыл", "тез арада", "жедел", "дереу", "24 сағат ішінде", "бір сағат ішінде",
            "соңғы күн", "соңғы ескерту", "кешіктірмей", "асығыңыз", "бүгін ғана",
            # en
            "urgent", "immediately", "within 24 hours", "act now", "asap",
            "final notice", "last chance", "expires today", "limited time", "hurry",
            "don't delay", "final warning",
        ),
    ),
    RuleGroup(
        "MONEY_TRANSFER", "Перевод денег", "Сообщение просит перевести деньги",
        (
            # ru
            "переведи", "перевести", "переведите", "перевод на", "скинь денег", "скиньте",
            "отправь деньги", "отправьте деньги", "пополните", "оплатите", "внесите",
            "займи денег", "нужны деньги", "оплата сбора", "ожидает оплаты",
            # kk
            "ақша аудар", "аударып жібер", "аударыңыз", "ақша жібер", "ақша сал", "төлеңіз",
            "төлем жаса", "шотқа сал", "теңге жібер", "қарызға бер", "ақша керек", "төлем күтілуде",
            # en
            "send money", "transfer money", "wire transfer", "pay now", "make a payment",
            "pay the fee", "bank transfer", "transfer the", "customs fee", "top up",
        ),
    ),
    RuleGroup(
        "BANK_CARD", "Банк и карта", "Упоминаются банк или банковская карта",
        (
            # ru
            "ваша карта", "вашей карт", "вашу карт", "банковск", "номер карт", "данные карт",
            "cvv", "cvc", "служба безопасности банка", "сотрудник банка", "kaspi", "halyk",
            "сбербанк", "с вашего счёта", "с вашего счета",
            # kk
            "картаңыз", "картаңызды", "банк қызмет", "банк карта", "банктен", "карта нөмір",
            "карта деректер", "шотыңыз", "шотыңыздан", "банк қауіпсіздік", "банк қызметкер",
            # en
            "your card", "credit card", "debit card", "card number", "bank account",
            "your bank", "card details", "account number", "security department", "banking",
        ),
    ),
    RuleGroup(
        "ACCOUNT_BLOCK", "Блокировка", "Упоминается блокировка карты или аккаунта",
        (
            # ru
            "заблокирован", "заблокируем", "будет заблокир", "блокировк", "приостановлен",
            "ограничен доступ", "доступ ограничен", "аккаунт взломан", "подозрительная операция",
            "подозрительной операц", "несанкционирован", "отключен",
            # kk
            "бұғатталды", "бұғатталады", "бұғаттал", "бұғаттау", "шектелді", "тоқтатылды",
            "тіркелгіңіз", "аккаунтыңыз", "күдікті операция", "күдікті әрекет", "рұқсатсыз",
            # en
            "suspended", "blocked", "locked", "deactivated", "disabled", "compromised",
            "unauthorized", "unauthorised", "suspicious activity", "restricted", "will be closed",
        ),
    ),
    RuleGroup(
        "PRIZE", "Выигрыш и приз", "Обещан выигрыш или приз",
        (
            # ru
            "вы выиграли", "выигрыш", "вы победитель", "ваш приз", "получите приз", "приз ",
            "подарок", "бонус", "лотере", "розыгрыш", "вам начислен", "компенсаци",
            # kk
            "ұтып алдыңыз", "ұтыс", "жеңімпаз", "сыйлық", "жүлде", "бонус алыңыз",
            "лотерея", "сізге есептелді", "өтемақы", "тегін алыңыз", "сыйақы",
            # en
            "you won", "you have won", "you've won", "winner", "congratulations", "prize",
            "claim", "free gift", "gift card", "reward", "lottery", "cash bonus", "selected to receive",
        ),
    ),
    RuleGroup(
        "CODE_REQUEST", "Запрос кода или пароля", "Просят сообщить код или пароль",
        (
            # ru
            "назовите код", "сообщите код", "продиктуйте код", "назови код", "код из sms",
            "код из смс", "введите код", "отправьте код", "скажите код", "назовите пароль",
            "сообщите пароль", "подтвердите данные", "введите пароль",
            # kk
            "кодты айтыңыз", "кодты жіберіңіз", "кодты енгізіңіз", "sms кодын", "смс кодын",
            "кодты хабарлаңыз", "құпиясөзді", "құпия сөзді", "кодын айт", "деректерді растаңыз",
            "растаңыз",
            # en
            "send the code", "tell me the code", "share the code", "enter the code",
            "your password", "verify your", "confirm your", "one-time password", "otp code",
            "code from sms", "provide your",
        ),
    ),
    RuleGroup(
        "AUTHORITY", "Ссылка на авторитет", "Отправитель выдаёт себя за организацию",
        (
            # ru
            "служба безопасности", "госуслуг", "egov", "полици", "прокуратур", "налогов",
            "штраф", "суд ", "центробанк", "нацбанк",
            # kk
            "қауіпсіздік қызметі", "полиция", "прокуратура", "салық", "айыппұл", "сот ",
            "ұлттық банк", "мемлекеттік қызмет", "уәкілетті", "электрондық үкімет",
            # en
            "police", "tax office", "government", "court order", "tax refund", "official notice",
            "fraud department", "customs", "traffic fine", "pay the fine",
        ),
    ),
    RuleGroup(
        "SECRECY", "Секретность", "Просят никому не рассказывать",
        (
            # ru
            "никому не говори", "никому не рассказ", "держи в секрете", "не говори никому",
            "это секрет", "между нами", "не звони", "не сообщай родн", "не сообщайте банк",
            "не рассказывай", "только тебе",
            # kk
            "ешкімге айтпа", "ешкімге айтпаңыз", "ешкімге білдірме", "құпия сақта", "құпия түрде",
            "біз екеуміз", "үйдегілерге айтпа", "банкке айтпаңыз", "хабарласпа", "сыр сақта",
            # en
            "don't tell", "do not tell", "keep it secret", "keep this secret", "between us",
            "tell no one", "don't call", "do not call", "confidential", "stay quiet",
        ),
    ),
)

RULES_BY_CODE = {group.code: group for group in RULE_GROUPS}


def _compile(phrases: tuple[str, ...]) -> re.Pattern:
    alternatives = "|".join(re.escape(p) for p in phrases)
    return re.compile(rf"(?<!\w)(?:{alternatives})")


_COMPILED = tuple((group.code, _compile(group.phrases)) for group in RULE_GROUPS)


def find_rule_groups(text: str) -> list[str]:
    """Вернуть коды сработавших групп в порядке их объявления."""
    if not isinstance(text, str) or not text:
        return []
    lowered = unicodedata.normalize("NFKC", text).lower()
    return [code for code, pattern in _COMPILED if pattern.search(lowered)]
