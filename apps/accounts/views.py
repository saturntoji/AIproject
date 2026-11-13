from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.forms import ChangePasswordForm, RegisterForm
from apps.accounts.models import UserProfile

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 60
LOCKOUT_MESSAGE = f"Слишком много неудачных попыток. Подождите {LOCKOUT_SECONDS} секунд."


def _failures_key(request, username: str) -> str:
    return f"login-failures:{username.lower()}:{request.META.get('REMOTE_ADDR', '')}"


def try_login(request, username: str, password: str) -> tuple[bool, str | None]:
    """Общая логика входа для формы и API: пауза 60 с после 5 неудачных попыток подряд (ФТ-1.3)."""
    key = _failures_key(request, username)
    failures = cache.get(key, 0)
    if failures >= MAX_FAILED_LOGINS:
        return False, LOCKOUT_MESSAGE
    user = authenticate(request, username=username, password=password)
    if user is None:
        cache.set(key, failures + 1, LOCKOUT_SECONDS)
        return False, "Неверный логин или пароль."
    cache.delete(key)
    login(request, user)
    return True, None


def create_user(form: RegisterForm):
    user = get_user_model().objects.create_user(
        username=form.cleaned_data["username"],
        email=form.cleaned_data["email"],
        password=form.cleaned_data["password"],
    )
    UserProfile.for_user(user)
    return user


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = None
    username = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        ok, error = try_login(request, username, request.POST.get("password", ""))
        if ok:
            next_url = request.POST.get("next", "")
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")
    return render(
        request,
        "accounts/login.html",
        {"error": error, "username": username, "next": request.GET.get("next", "")},
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, create_user(form))
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    profile = UserProfile.for_user(request.user)
    password_form = ChangePasswordForm(request.user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "consent":
            profile.store_sms_text = request.POST.get("store_sms_text") == "on"
            profile.save(update_fields=["store_sms_text"])
            messages.success(request, "Настройка сохранена.")
        elif action == "delete_history":
            deleted = request.user.checks.count()
            request.user.checks.all().delete()
            messages.success(request, f"История удалена. Записей: {deleted}.")
        elif action == "password":
            password_form = ChangePasswordForm(request.user, request.POST)
            if not password_form.is_valid():
                return render(
                    request,
                    "accounts/profile.html",
                    {"profile": profile, "password_form": password_form, "active": "profile"},
                )
            update_session_auth_hash(request, password_form.save())
            messages.success(request, "Пароль изменён.")
        return redirect("profile")
    return render(
        request,
        "accounts/profile.html",
        {"profile": profile, "password_form": password_form, "active": "profile"},
    )
