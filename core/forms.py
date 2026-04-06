# Импортируем встроенную форму создания пользователя.
from django.contrib.auth.forms import UserCreationForm

# Импортируем модель пользователя Django.
from django.contrib.auth.models import User

# Импортируем модуль forms для создания форм.
from django import forms

# Импортируем локальные модели.
from core.models import Category, SavedReport, Transaction, UserProfile


class RegisterForm(UserCreationForm):
    # Добавляем поле email в форму регистрации.
    email = forms.EmailField(required=False, label="Email")

    class Meta:
        # Указываем модель формы.
        model = User

        # Указываем порядок и список полей формы.
        fields = ("username", "email", "password1", "password2")


class TransactionForm(forms.ModelForm):
    class Meta:
        # Указываем модель формы.
        model = Transaction

        # Указываем поля формы.
        fields = ("transaction_type", "amount", "operation_date", "category", "description")

        # Настраиваем виджеты формы для более удобного UI.
        widgets = {
            "transaction_type": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Например, 1500.00"}),
            "operation_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Короткое описание операции"}),
        }

        # Подписываем поля формы.
        labels = {
            "transaction_type": "Тип операции",
            "amount": "Сумма",
            "operation_date": "Дата",
            "category": "Категория",
            "description": "Описание",
        }

    def __init__(self, *args, **kwargs):
        # Извлекаем пользователя из именованных аргументов.
        user = kwargs.pop("user", None)

        # Инициализируем родительскую форму.
        super().__init__(*args, **kwargs)

        # Если пользователь передан, ограничиваем список категорий только его категориями.
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user, is_active=True)


class CategoryForm(forms.ModelForm):
    class Meta:
        # Указываем модель формы.
        model = Category

        # Указываем поля формы.
        fields = ("name", "icon", "monthly_limit", "is_active")

        # Настраиваем виджеты формы.
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например, Еда"}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например, 🍔"}),
            "monthly_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        # Подписываем поля формы.
        labels = {
            "name": "Название",
            "icon": "Иконка",
            "monthly_limit": "Лимит на месяц",
            "is_active": "Активна",
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        # Указываем модель формы.
        model = UserProfile

        # Указываем поля формы.
        fields = ("budget_limit", "daily_reports_enabled", "weekly_reports_enabled", "recommendations_enabled")

        # Настраиваем виджеты формы.
        widgets = {
            "budget_limit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "daily_reports_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "weekly_reports_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "recommendations_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        # Подписываем поля формы.
        labels = {
            "budget_limit": "Общий месячный лимит",
            "daily_reports_enabled": "Ежедневные Telegram-отчёты",
            "weekly_reports_enabled": "Еженедельные Telegram-отчёты",
            "recommendations_enabled": "Показывать рекомендации",
        }


class SavedReportForm(forms.ModelForm):
    class Meta:
        # Указываем модель формы.
        model = SavedReport

        # Указываем поля формы.
        fields = ("name", "period", "start_date", "end_date", "category")

        # Настраиваем виджеты формы.
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например, Мой месячный анализ"}),
            "period": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "category": forms.Select(attrs={"class": "form-select"}),
        }

        # Подписываем поля формы.
        labels = {
            "name": "Название отчёта",
            "period": "Период",
            "start_date": "Дата начала",
            "end_date": "Дата конца",
            "category": "Категория",
        }

    def __init__(self, *args, **kwargs):
        # Извлекаем пользователя из именованных аргументов.
        user = kwargs.pop("user", None)

        # Инициализируем родительскую форму.
        super().__init__(*args, **kwargs)

        # Если пользователь передан, ограничиваем категории только его списком.
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user, is_active=True)

        # Разрешаем оставить категорию пустой.
        self.fields["category"].required = False
