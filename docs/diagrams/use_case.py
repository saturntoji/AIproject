"""Рисует docs/figures/use_case.png по той же схеме, что и use_case.puml.

Запуск из корня проекта: python docs/diagrams/use_case.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch

OUTPUT = Path(__file__).resolve().parents[1] / "figures" / "use_case.png"
CASES = [
    "UC-1 Зарегистрироваться",
    "UC-2 Войти и выйти",
    "UC-3 Проверить SMS",
    "UC-4 Проверить URL",
    "UC-5 Посмотреть результат",
    "UC-6 История и фильтры",
    "UC-7 Удалить запись или историю",
    "UC-8 Посмотреть Dashboard",
    "UC-9 Согласие на хранение текста",
    "UC-10 Статистика по всей системе",
    "UC-11 Версии и метрики моделей",
]
USER_CASES = {0, 1, 2, 3, 4, 5, 6, 7, 8}
ADMIN_CASES = {1, 7, 9, 10}
ROW = 1.0
CENTER_X = 6.0


def draw_actor(ax, x, y, name):
    ax.add_patch(plt.Circle((x, y + 0.45), 0.16, fill=False, lw=1.6))
    ax.plot([x, x], [y + 0.29, y - 0.25], color="black", lw=1.6)
    ax.plot([x - 0.3, x + 0.3], [y + 0.1, y + 0.1], color="black", lw=1.6)
    ax.plot([x, x - 0.25], [y - 0.25, y - 0.65], color="black", lw=1.6)
    ax.plot([x, x + 0.25], [y - 0.25, y - 0.65], color="black", lw=1.6)
    ax.text(x, y - 0.95, name, ha="center", fontsize=11)


def main():
    fig, ax = plt.subplots(figsize=(11, 9))
    top = (len(CASES) - 1) * ROW
    ax.add_patch(FancyBboxPatch((2.9, -0.7), 6.2, top + 1.6, boxstyle="round,pad=0.02", fill=False, lw=1.2))
    ax.text(CENTER_X, top + 0.6, "SMS Guard", ha="center", fontsize=13, fontweight="bold")

    user_pos, admin_pos = (0.8, top / 2), (11.2, top / 2)
    draw_actor(ax, *user_pos, "Пользователь")
    draw_actor(ax, *admin_pos, "Администратор")

    for index, title in enumerate(CASES):
        y = top - index * ROW
        ax.add_patch(Ellipse((CENTER_X, y), 5.6, 0.72, fill=True, facecolor="#e6eefb", edgecolor="#2259c7"))
        ax.text(CENTER_X, y, title, ha="center", va="center", fontsize=10.5)
        if index in USER_CASES:
            ax.plot([user_pos[0] + 0.4, CENTER_X - 2.8], [user_pos[1], y], color="#5b6472", lw=0.9)
        if index in ADMIN_CASES:
            ax.plot([admin_pos[0] - 0.4, CENTER_X + 2.8], [admin_pos[1], y], color="#5b6472", lw=0.9)

    between_uc3_and_uc4 = top - 2.5 * ROW
    ax.annotate(
        "«include»: ссылки из текста",
        xy=(CENTER_X + 2.1, top - 3 * ROW + 0.26),
        xytext=(CENTER_X, between_uc3_and_uc4),
        ha="center",
        va="center",
        fontsize=8,
        arrowprops={"arrowstyle": "->", "linestyle": "dashed"},
    )
    ax.set_xlim(-0.2, 12.2)
    ax.set_ylim(-1.2, top + 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=130)


if __name__ == "__main__":
    main()
