# Импортируем timedelta, чтобы уметь считать границы недель и других периодов.
from datetime import timedelta

# Импортируем sync_to_async, чтобы безопасно вызывать Django ORM из асинхронного Telegram-бота.
from asgiref.sync import sync_to_async

# Импортируем timezone, чтобы работать с локальной датой проекта.
from django.utils import timezone

# Импортируем Sum, чтобы считать суммы по операциям через Django ORM.
from django.db.models import Sum

# Импортируем модели проекта, которые используются Telegram-ботом.
from core.models import Category, NotificationHistory, Transaction, UserProfile

# Импортируем общий сервис аналитической текстовой сводки.
from core.services.analytics import build_text_summary_for_period


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def link_telegram_account(code: str, telegram_id: int) -> tuple[bool, str]:
    # Ищем профиль пользователя по коду привязки Telegram.
    profile = UserProfile.objects.filter(telegram_link_code=code).select_related("user").first()

    # Проверяем, найден ли профиль.
    if not profile:
        # Если профиль не найден, возвращаем понятное сообщение об ошибке.
        return False, "Код привязки не найден. Проверьте его в личном кабинете."

    # Проверяем, не привязан ли уже этот Telegram ID к другому аккаунту.
    if UserProfile.objects.filter(telegram_id=telegram_id).exclude(pk=profile.pk).exists():
        # Если Telegram уже занят другим аккаунтом, возвращаем отказ.
        return False, "Этот Telegram уже привязан к другому аккаунту."

    # Записываем Telegram ID в профиль.
    profile.telegram_id = telegram_id

    # Обновляем код привязки, чтобы старый код больше нельзя было использовать повторно.
    profile.regenerate_telegram_code()

    # Сохраняем изменения профиля.
    profile.save()

    # Возвращаем успешный результат привязки.
    return True, f"Аккаунт {profile.user.username} успешно привязан к Telegram."


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    # Ищем профиль по Telegram ID и сразу подтягиваем связанного пользователя.
    profile = UserProfile.objects.filter(telegram_id=telegram_id).select_related("user").first()

    # Проверяем, найден ли профиль.
    if profile:
        # Если профиль найден, возвращаем пользователя.
        return profile.user

    # Если профиль не найден, возвращаем None.
    return None


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def get_today_expenses_text(user) -> str:
    # Получаем сегодняшнюю локальную дату проекта.
    today = timezone.localdate()

    # Получаем все операции пользователя за сегодня.
    queryset = (
        Transaction.objects.filter(
            user=user,
            operation_date=today,
        )
        .select_related("category")
        .order_by("-created_at")
    )

    # Строим общую текстовую сводку за день через единый сервис аналитики.
    summary_text = build_text_summary_for_period(user, period="day")

    # Проверяем, есть ли сегодня операции вообще.
    if not queryset.exists():
        # Если операций нет, возвращаем сводку и пояснение.
        return f"{summary_text}\n\nСегодня операций пока нет."

    # Создаём список строк будущего ответа.
    lines = []

    # Добавляем в начало ответа готовую дневную сводку.
    lines.append(summary_text)

    # Добавляем пустую строку для визуального разделения блоков.
    lines.append("")

    # Отбираем сегодняшние доходы пользователя.
    income_items = queryset.filter(transaction_type=Transaction.TYPE_INCOME)

    # Проверяем, есть ли доходы за сегодня.
    if income_items.exists():
        # Добавляем заголовок блока доходов.
        lines.append("💰 Доходы за сегодня:")

        # Проходим по каждой доходной операции.
        for item in income_items:
            # Добавляем строку с иконкой категории, названием, суммой и описанием операции.
            lines.append(
                f"• {item.category.icon} {item.category.name}: {item.amount:.2f} — "
                f"{item.description or 'без описания'}"
            )

        # Добавляем пустую строку после блока доходов.
        lines.append("")

    # Отбираем сегодняшние расходы пользователя.
    expense_items = queryset.filter(transaction_type=Transaction.TYPE_EXPENSE)

    # Проверяем, есть ли расходы за сегодня.
    if expense_items.exists():
        # Добавляем заголовок блока расходов.
        lines.append("🧾 Расходы за сегодня:")

        # Проходим по каждой расходной операции.
        for item in expense_items:
            # Добавляем строку с иконкой категории, названием, суммой и описанием операции.
            lines.append(
                f"• {item.category.icon} {item.category.name}: {item.amount:.2f} — "
                f"{item.description or 'без описания'}"
            )

    # Возвращаем собранный текст без лишних пустых хвостов.
    return "\n".join(lines).strip()


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def get_week_summary_text(user) -> str:
    # Возвращаем готовую недельную сводку через общий сервис аналитики.
    return build_text_summary_for_period(user, period="week")


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def get_category_report_text(user, category_name: str) -> str:
    # Ищем категорию пользователя по частичному совпадению имени без учёта регистра.
    category = Category.objects.filter(user=user, name__icontains=category_name).first()

    # Проверяем, найдена ли категория.
    if not category:
        # Если категория не найдена, возвращаем понятное сообщение.
        return "Категория не найдена. Проверьте название и попробуйте снова."

    # Вычисляем дату начала периода в 7 дней.
    start_date = timezone.localdate() - timedelta(days=6)

    # Получаем расходы пользователя по выбранной категории за последние 7 дней.
    queryset = Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.TYPE_EXPENSE,
        category=category,
        operation_date__gte=start_date,
    )

    # Считаем общую сумму расходов по категории.
    total = sum(item.amount for item in queryset)

    # Возвращаем итоговый текст по категории.
    return f"{category.icon} Категория «{category.name}» за последние 7 дней: {total:.2f}"


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def add_transaction_from_bot(user, transaction_type: str, amount: float, category_id: int, description: str) -> str:
    # Ищем активную категорию пользователя по ID.
    category = Category.objects.filter(user=user, id=category_id, is_active=True).first()

    # Проверяем, найдена ли категория.
    if not category:
        # Если категория не найдена, возвращаем сообщение об ошибке.
        return "Категория не найдена."

    # Создаём новую финансовую операцию от имени пользователя.
    Transaction.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=amount,
        operation_date=timezone.localdate(),
        category=category,
        description=description,
    )

    # Возвращаем подтверждение успешного сохранения операции.
    return f"Операция сохранена: {category.icon} {category.name} — {amount:.2f}"


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def get_categories_for_user(user) -> list[tuple[int, str]]:
    # Возвращаем список активных категорий пользователя для Telegram-клавиатуры.
    return [
        (category.id, f"{category.icon} {category.name}")
        for category in user.categories.filter(is_active=True).order_by("name")
    ]


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def get_compare_week_text(user) -> str:
    # Получаем сегодняшнюю локальную дату.
    today = timezone.localdate()

    # Определяем начало текущего недельного периода.
    current_start = today - timedelta(days=6)

    # Определяем конец прошлого недельного периода.
    previous_end = current_start - timedelta(days=1)

    # Определяем начало прошлого недельного периода.
    previous_start = previous_end - timedelta(days=6)

    # Считаем расходы пользователя за текущую неделю.
    current_total = (
        Transaction.objects.filter(
            user=user,
            transaction_type=Transaction.TYPE_EXPENSE,
            operation_date__range=(current_start, today),
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # Считаем расходы пользователя за прошлую неделю.
    previous_total = (
        Transaction.objects.filter(
            user=user,
            transaction_type=Transaction.TYPE_EXPENSE,
            operation_date__range=(previous_start, previous_end),
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    # Вычисляем разницу между двумя неделями.
    difference = current_total - previous_total

    # Проверяем, выросли ли расходы относительно прошлой недели.
    if difference > 0:
        # Формируем текст о росте расходов.
        trend = f"Расходы выросли на {difference:.2f}"

    # Проверяем, снизились ли расходы относительно прошлой недели.
    elif difference < 0:
        # Формируем текст о снижении расходов.
        trend = f"Расходы снизились на {abs(difference):.2f}"

    # Если разницы нет, пишем об этом прямо.
    else:
        # Формируем нейтральный итог.
        trend = "Расходы не изменились."

    # Возвращаем готовый текст сравнения недель.
    return (
        f"📈 Сравнение недель\n"
        f"• Текущая неделя: {current_total:.2f}\n"
        f"• Прошлая неделя: {previous_total:.2f}\n"
        f"• Итог: {trend}"
    )


# Делаем функцию безопасной для асинхронного вызова из aiogram.
@sync_to_async
def write_notification_history(user, notification_type: str, message: str, is_success: bool = True) -> None:
    # Сохраняем факт отправки уведомления в историю уведомлений.
    NotificationHistory.objects.create(
        user=user,
        channel=NotificationHistory.CHANNEL_TELEGRAM,
        notification_type=notification_type,
        message=message,
        is_success=is_success,
    )