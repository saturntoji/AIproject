import re

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")


class RegisterForm(forms.Form):
    username = forms.CharField(label="Логин", max_length=30, error_messages={"required": "Введите логин."})
    email = forms.EmailField(
        label="E-mail",
        error_messages={"required": "Введите e-mail.", "invalid": "Введите корректный e-mail."},
    )
    password = forms.CharField(
        label="Пароль", widget=forms.PasswordInput, error_messages={"required": "Введите пароль."}
    )
    password2 = forms.CharField(
        label="Повторите пароль", widget=forms.PasswordInput, error_messages={"required": "Повторите пароль."}
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not USERNAME_RE.match(username):
            raise forms.ValidationError("Логин: 3–30 символов, латиница, цифры и _.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Такой логин уже занят.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Такой e-mail уже зарегистрирован.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if len(password) < 8 or not re.search(r"[^\W\d_]", password) or not re.search(r"\d", password):
            raise forms.ValidationError("Пароль: не менее 8 символов, буквы и цифры.")
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password2") and cleaned["password"] != cleaned["password2"]:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned
