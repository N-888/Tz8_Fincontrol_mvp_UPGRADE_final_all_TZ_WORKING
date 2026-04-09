# Импортируем встроенную форму создания пользователя.
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from core.models import Category, SavedReport, Transaction, UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, label="Email")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("transaction_type", "amount", "operation_date", "category", "description")
        widgets = {
            "transaction_type": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Например, 1500.00"}),
            "operation_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Короткое описание операции"}),
        }
        labels = {
            "transaction_type": "Тип операции",
            "amount": "Сумма",
            "operation_date": "Дата",
            "category": "Категория / подкатегория",
            "description": "Описание",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user, is_active=True).select_related("parent")
            self.fields["category"].label_from_instance = lambda obj: f"{obj.icon} {obj.full_name}"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "icon", "parent", "monthly_limit", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например, Еда"}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например, 🍔"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "monthly_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "Название",
            "icon": "Иконка",
            "parent": "Родительская категория",
            "monthly_limit": "Лимит на месяц",
            "is_active": "Активна",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["parent"].required = False
        if user is not None:
            queryset = Category.objects.filter(user=user, is_active=True).select_related("parent")
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = queryset
            self.fields["parent"].label_from_instance = lambda obj: f"{obj.icon} {obj.full_name}"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = (
            "budget_limit",
            "daily_reports_enabled",
            "weekly_reports_enabled",
            "recommendations_enabled",
            "ai_advice_enabled",
            "telegram_voice_enabled",
        )
        widgets = {
            "budget_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "daily_reports_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "weekly_reports_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "recommendations_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ai_advice_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "telegram_voice_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "budget_limit": "Общий месячный лимит",
            "daily_reports_enabled": "Ежедневные Telegram-отчёты",
            "weekly_reports_enabled": "Еженедельные Telegram-отчёты",
            "recommendations_enabled": "Показывать бесплатные рекомендации и предупреждения",
            "ai_advice_enabled": "Включить расширенные AI-подсказки (дополнительная опция)",
            "telegram_voice_enabled": "Включить голосовой ввод через Telegram (дополнительная опция)",
        }


class SavedReportForm(forms.ModelForm):
    class Meta:
        model = SavedReport
        fields = ("name", "period", "start_date", "end_date", "category")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например, Мой месячный анализ"}),
            "period": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "category": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "name": "Название отчёта",
            "period": "Период",
            "start_date": "Дата начала",
            "end_date": "Дата конца",
            "category": "Категория / подкатегория",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user, is_active=True).select_related("parent")
            self.fields["category"].label_from_instance = lambda obj: f"{obj.icon} {obj.full_name}"
        self.fields["category"].required = False
