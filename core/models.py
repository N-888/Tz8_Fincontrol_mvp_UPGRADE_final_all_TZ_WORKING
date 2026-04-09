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

    # Храним флаг включения расширенных AI-подсказок.
    ai_advice_enabled = models.BooleanField(default=False)

    # Храним флаг включения голосового ввода через Telegram.
    telegram_voice_enabled = models.BooleanField(default=False)

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

    # Храним родительскую категорию, если текущая запись является подкатегорией.
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
    )

    # Храним необязательный месячный лимит по категории.
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Храним признак активности категории.
    is_active = models.BooleanField(default=True)

    # Храним дату создания категории.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Указываем сортировку категорий сначала по родителю, потом по имени.
        ordering = ["parent__name", "name"]

        # Запрещаем дублировать названия категорий у одного пользователя.
        unique_together = ("user", "parent", "name")

    @property
    def full_name(self) -> str:
        # Если категория является подкатегорией, возвращаем полный путь.
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def __str__(self) -> str:
        # Возвращаем строку с иконкой и полным названием категории.
        return f"{self.icon} {self.full_name}"


class Transaction(models.Model):
    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"

    TYPE_CHOICES = [
        (TYPE_INCOME, "Доход"),
        (TYPE_EXPENSE, "Расход"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    operation_date = models.DateField(default=timezone.localdate)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="transactions")
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-operation_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} {self.amount} {self.category.full_name}"


class Advice(models.Model):
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"

    LEVEL_CHOICES = [
        (LEVEL_INFO, "Информация"),
        (LEVEL_WARNING, "Предупреждение"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="advices")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    text = models.TextField()
    code = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.level}: {self.text[:50]}"


class Anomaly(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="anomalies")
    title = models.CharField(max_length=150)
    details = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        return self.title


class NotificationHistory(models.Model):
    CHANNEL_TELEGRAM = "telegram"

    CHANNEL_CHOICES = [
        (CHANNEL_TELEGRAM, "Telegram"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_TELEGRAM)
    notification_type = models.CharField(max_length=50)
    message = models.TextField()
    is_success = models.BooleanField(default=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"{self.user.username} / {self.notification_type}"


class SavedReport(models.Model):
    PERIOD_CHOICES = [
        ("day", "День"),
        ("week", "Неделя"),
        ("month", "Месяц"),
        ("year", "Год"),
        ("custom", "Произвольный период"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_reports")
    name = models.CharField(max_length=120)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="month")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
