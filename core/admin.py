# Импортируем административный модуль Django.
from django.contrib import admin

# Импортируем модели проекта.
from core.models import Advice, Anomaly, Category, NotificationHistory, SavedReport, Transaction, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке профилей.
    list_display = ("user", "telegram_id", "budget_limit", "daily_reports_enabled", "weekly_reports_enabled")

    # Указываем поля для быстрого поиска.
    search_fields = ("user__username", "telegram_link_code", "telegram_id")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке категорий.
    list_display = ("name", "icon", "user", "monthly_limit", "is_active")

    # Указываем поля для поиска.
    search_fields = ("name", "user__username")

    # Указываем фильтры справа.
    list_filter = ("is_active",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке операций.
    list_display = ("user", "transaction_type", "amount", "operation_date", "category")

    # Указываем поля для поиска.
    search_fields = ("user__username", "description", "category__name")

    # Указываем фильтры справа.
    list_filter = ("transaction_type", "operation_date", "category")


@admin.register(Advice)
class AdviceAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке советов.
    list_display = ("user", "level", "code", "created_at")

    # Указываем поля для поиска.
    search_fields = ("user__username", "text", "code")


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке аномалий.
    list_display = ("user", "title", "category", "detected_at")

    # Указываем поля для поиска.
    search_fields = ("user__username", "title", "details")


@admin.register(NotificationHistory)
class NotificationHistoryAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке уведомлений.
    list_display = ("user", "channel", "notification_type", "is_success", "sent_at")

    # Указываем поля для поиска.
    search_fields = ("user__username", "notification_type", "message")


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    # Указываем поля для отображения в списке сохранённых отчётов.
    list_display = ("user", "name", "period", "start_date", "end_date", "category", "created_at")

    # Указываем поля для поиска.
    search_fields = ("user__username", "name")
