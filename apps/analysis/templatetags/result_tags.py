from django import template
from django.utils.html import format_html

from apps.analysis.services import check_fragment

register = template.Library()

_BADGES = {
    ("SAFE", "SMS"): ("safe", "✓", "Безопасное"),
    ("SAFE", "URL"): ("safe", "✓", "Безопасная"),
    ("SUSPICIOUS", "SMS"): ("warn", "!", "Подозрительное"),
    ("SUSPICIOUS", "URL"): ("warn", "!", "Подозрительная"),
    ("FRAUDULENT", "SMS"): ("danger", "⚠", "Мошенническое"),
    ("DANGEROUS", "URL"): ("danger", "⚠", "Опасная"),
}


@register.simple_tag
def category_badge(check):
    css, icon, label = _BADGES[(check.category, check.check_type)]
    return format_html('<span class="badge-risk badge-{}"><span aria-hidden="true">{}</span> {}</span>', css, icon, label)


@register.filter
def fragment(check):
    return check_fragment(check)
