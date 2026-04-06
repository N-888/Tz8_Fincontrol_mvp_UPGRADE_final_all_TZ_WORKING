# Импортируем uuid, чтобы создавать уникальные коды привязки Telegram.
import uuid

# Импортируем стандартную модель пользователя Django.
from django.contrib.auth.models import User

# Импортируем инструменты ORM Django.
from django.db import models

# Импортируем функции времени Django.
from django.utils import timezone


class UserProfile(models.Model):
    # Связываем профиль с базовой учётной записью пользователя.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Храним Telegram ID после привязки бота.
    telegram_id = models.BigIntegerField(blank=True, null=True, unique=True)

    # Храним уникальный код для безопасной привязки Telegram.
    telegram_link_code = models.CharField(max_length=32, unique=True, default="", blank=True)

    # Храним общий месячный лимит пользователя.
    budget_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Храним флаг ежедневных уведомлений.
    daily_reports_enabled = models.BooleanField(default=True)

    # Храним флаг еженедельных уведомлений.
    weekly_reports_enabled = models.BooleanField(default=False)

    # Храним флаг показа рекомендаций.
    recommendations_enabled = models.BooleanField(default=True)

    # Храним дату обновления профиля.
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Проверяем, есть ли код привязки Telegram.
        if not self.telegram_link_code:
            # Создаём короткий уникальный код без дефисов.
            self.telegram_link_code = uuid.uuid4().hex[:12].upper()

        # Сохраняем профиль стандартным способом.
        super().save(*args, **kwargs)

    def regenerate_telegram_code(self) -> None:
        # Создаём новый код привязки Telegram.
        self.telegram_link_code = uuid.uuid4().hex[:12].upper()

        # Сохраняем профиль с новым кодом.
        self.save(update_fields=["telegram_link_code", "updated_at"])

    def __str__(self) -> str:
        # Возвращаем понятное строковое представление профиля.
        return f"Профиль {self.user.username}"


class Category(models.Model):
    # Связываем категорию с владельцем.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")

    # Храним название категории.
    name = models.CharField(max_length=100)

    # Храним эмодзи или иконку для красивого отображения.
    icon = models.CharField(max_length=10, default="💼")

    # Храним необязательный месячный лимит по категории.
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Храним признак активности категории.
    is_active = models.BooleanField(default=True)

    # Храним дату создания категории.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку категорий по имени.
        ordering = ["name"]

        # Запрещаем дублировать названия категорий у одного пользователя.
        unique_together = ("user", "name")

    def __str__(self) -> str:
        # Возвращаем строку с иконкой и названием категории.
        return f"{self.icon} {self.name}"


class Transaction(models.Model):
    # Описываем варианты типов операции.
    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"

    # Создаём список вариантов типов операции.
    TYPE_CHOICES = [
        (TYPE_INCOME, "Доход"),
        (TYPE_EXPENSE, "Расход"),
    ]

    # Связываем операцию с владельцем.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")

    # Храним тип операции.
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    # Храним сумму операции.
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Храним дату операции.
    operation_date = models.DateField(default=timezone.localdate)

    # Связываем операцию с категорией.
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")

    # Храним описание операции.
    description = models.CharField(max_length=255, blank=True)

    # Храним дату и время создания записи.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку списка операций.
        ordering = ["-operation_date", "-created_at"]

    def __str__(self) -> str:
        # Возвращаем компактное строковое представление операции.
        return f"{self.get_transaction_type_display()} {self.amount} {self.category.name}"


class Advice(models.Model):
    # Описываем уровень совета.
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"

    # Создаём список вариантов уровня совета.
    LEVEL_CHOICES = [
        (LEVEL_INFO, "Информация"),
        (LEVEL_WARNING, "Предупреждение"),
    ]

    # Связываем совет с владельцем.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advices")

    # Храним уровень важности совета.
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)

    # Храним сам текст совета.
    text = models.TextField()

    # Храним технический ключ, чтобы не плодить дубликаты одинаковых советов.
    code = models.CharField(max_length=100)

    # Храним дату создания совета.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку по свежести.
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # Возвращаем компактный текст совета.
        return f"{self.level}: {self.text[:50]}"


class Anomaly(models.Model):
    # Связываем аномалию с владельцем.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="anomalies")

    # Храним заголовок аномалии.
    title = models.CharField(max_length=150)

    # Храним подробное описание аномалии.
    details = models.TextField()

    # Храним необязательную категорию, если аномалия относится к ней.
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)

    # Храним дату обнаружения аномалии.
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку по свежести.
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        # Возвращаем короткое представление аномалии.
        return self.title


class NotificationHistory(models.Model):
    # Описываем варианты канала уведомлений.
    CHANNEL_TELEGRAM = "telegram"

    # Создаём список вариантов каналов.
    CHANNEL_CHOICES = [
        (CHANNEL_TELEGRAM, "Telegram"),
    ]

    # Связываем уведомление с владельцем.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")

    # Храним канал отправки.
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_TELEGRAM)

    # Храним тип уведомления.
    notification_type = models.CharField(max_length=50)

    # Храним текст отправленного уведомления.
    message = models.TextField()

    # Храним флаг успешной отправки.
    is_success = models.BooleanField(default=True)

    # Храним время отправки.
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку по свежести.
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        # Возвращаем короткое представление уведомления.
        return f"{self.user.username} / {self.notification_type}"


class SavedReport(models.Model):
    # Описываем допустимые периоды для сохранённого отчёта.
    PERIOD_CHOICES = [
        ("day", "День"),
        ("week", "Неделя"),
        ("month", "Месяц"),
        ("year", "Год"),
        ("custom", "Произвольный период"),
    ]

    # Связываем сохранённый отчёт с владельцем.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_reports")

    # Храним имя отчёта, которое придумал пользователь.
    name = models.CharField(max_length=120)

    # Храним выбранный период.
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="month")

    # Храним дату начала, если нужен произвольный период.
    start_date = models.DateField(blank=True, null=True)

    # Храним дату окончания, если нужен произвольный период.
    end_date = models.DateField(blank=True, null=True)

    # Храним выбранную категорию, если отчёт фиксируется по одной категории.
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)

    # Храним дату создания избранного отчёта.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку по свежести.
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # Возвращаем имя сохранённого отчёта.
        return self.name
