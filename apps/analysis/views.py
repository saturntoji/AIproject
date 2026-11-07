from django.http import JsonResponse
from django.shortcuts import render


def health(request):
    return JsonResponse({"status": "ok"})


def check_sms_page(request):
    return render(request, "analysis/check_sms.html", {"active": "sms"})


def check_url_page(request):
    return render(request, "analysis/check_url.html", {"active": "url"})


def history_page(request):
    return render(request, "analysis/history.html", {"active": "history"})
