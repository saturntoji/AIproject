"""Рисует docs/figures/er_diagram.png по схеме из er.puml (задание 16).

Запуск из корня проекта: python docs/diagrams/er_diagram.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUTPUT = Path(__file__).resolve().parents[1] / "figures" / "er_diagram.png"
LINE = 0.34
TABLES = {
    "auth_user": ((0.3, 9.6), ["id PK", "username", "email", "password (хеш)", "is_staff", "date_joined"]),
    "accounts_userprofile": ((0.3, 4.6), ["id PK", "user_id FK, UNIQUE", "store_sms_text", "preferred_language"]),
    "analysis_check": ((5.0, 9.6), [
        "id PK", "user_id FK", "check_type", "input_text NULL", "input_masked", "language", "category",
        "risk_level", "risk_score", "p_sms NULL", "explanation", "recommendation",
        "sms_model_version", "url_model_version", "created_at",
    ]),
    "analysis_urlresult": ((10.0, 9.6), ["id PK", "check_id FK", "url", "domain", "p_url", "category", "features_json"]),
    "analysis_detectedfeature": ((10.0, 5.6), ["id PK", "check_id FK", "code", "title", "weight"]),
    "analysis_modelversion (справочная)": ((5.0, 3.5), ["id PK", "model_type", "version", "algorithm", "metrics_json", "threshold", "trained_at", "is_active"]),
}
WIDTH = 3.6
LINKS = [
    ("auth_user", "accounts_userprofile", "1 : 1"),
    ("auth_user", "analysis_check", "1 : N"),
    ("analysis_check", "analysis_urlresult", "1 : N"),
    ("analysis_check", "analysis_detectedfeature", "1 : N"),
]


def box(ax, name, x, y, fields):
    height = LINE * (len(fields) + 1.3)
    ax.add_patch(FancyBboxPatch((x, y - height), WIDTH, height, boxstyle="round,pad=0.02", fc="#ffffff", ec="#2259c7", lw=1.4))
    ax.add_patch(FancyBboxPatch((x, y - LINE * 1.2), WIDTH, LINE * 1.2, boxstyle="round,pad=0.02", fc="#e6eefb", ec="#2259c7", lw=1.4))
    ax.text(x + WIDTH / 2, y - LINE * 0.6, name, ha="center", va="center", fontsize=10, fontweight="bold")
    for i, field in enumerate(fields):
        ax.text(x + 0.15, y - LINE * (1.8 + i), field, va="center", fontsize=8.5)
    return height


def main():
    fig, ax = plt.subplots(figsize=(14, 9))
    geometry = {}
    for name, ((x, y), fields) in TABLES.items():
        geometry[name] = (x, y, box(ax, name, x, y, fields))
    for source, target, label in LINKS:
        sx, sy, sh = geometry[source]
        tx, ty, th = geometry[target]
        if abs(sx - tx) < 0.1:
            start, end = (sx + WIDTH / 2, sy - sh), (tx + WIDTH / 2, ty)
        else:
            start, end = (sx + WIDTH, sy - LINE * 2), (tx, ty - LINE * 2 - (0 if ty == sy else 0))
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "-|>", "color": "#5b6472", "lw": 1.2})
        ax.text((start[0] + end[0]) / 2 + 0.12, (start[1] + end[1]) / 2 + 0.15, label, ha="left", fontsize=9, color="#5b6472")
    ax.set_xlim(0, 14)
    ax.set_ylim(-0.5, 10)
    ax.axis("off")
    ax.set_title("ER-диаграмма базы данных SMS Guard", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=120)


if __name__ == "__main__":
    main()
