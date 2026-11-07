from django.shortcuts import render

# Условная высота столбиков на макете, %.
DEMO_BARS = [38, 52, 26, 64, 46, 72, 40, 58, 80, 52, 66, 34, 78, 62, 92]


def dashboard_page(request):
    return render(request, "dashboard/dashboard.html", {"active": "dashboard", "bars": DEMO_BARS})
