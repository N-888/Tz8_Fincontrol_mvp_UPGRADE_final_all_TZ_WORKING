# Импортируем timedelta, чтобы уметь считать границы недель и других периодов.
from datetime import timedelta
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Sum
from core.models import Category, NotificationHistory, Transaction, UserProfile
from core.services.analytics import build_text_summary_for_period
from core.services.ai_features import parse_transaction_text


@sync_to_async
def link_telegram_account(code: str, telegram_id: int) -> tuple[bool, str]:
    profile = UserProfile.objects.filter(telegram_link_code=code).select_related("user").first()
    if not profile:
        return False, "Код привязки не найден. Проверьте его в личном кабинете."
    if UserProfile.objects.filter(telegram_id=telegram_id).exclude(pk=profile.pk).exists():
        return False, "Этот Telegram уже привязан к другому аккаунту."
    profile.telegram_id = telegram_id
    profile.regenerate_telegram_code()
    profile.save()
    return True, f"Аккаунт {profile.user.username} успешно привязан к Telegram."


@sync_to_async
def get_user_by_telegram_id(telegram_id: int):
    profile = UserProfile.objects.filter(telegram_id=telegram_id).select_related("user").first()
    if profile:
        return profile.user
    return None


@sync_to_async
def get_today_expenses_text(user) -> str:
    today = timezone.localdate()
    queryset = (
        Transaction.objects.filter(user=user, operation_date=today)
        .select_related("category", "category__parent")
        .order_by("-created_at")
    )
    summary_text = build_text_summary_for_period(user, period="day")
    if not queryset.exists():
        return f"{summary_text}\n\nСегодня операций пока нет."
    lines = [summary_text, ""]
    income_items = queryset.filter(transaction_type=Transaction.TYPE_INCOME)
    if income_items.exists():
        lines.append("💰 Доходы за сегодня:")
        for item in income_items:
            lines.append(f"• {item.category.icon} {item.category.full_name}: {item.amount:.2f} — {item.description or 'без описания'}")
        lines.append("")
    expense_items = queryset.filter(transaction_type=Transaction.TYPE_EXPENSE)
    if expense_items.exists():
        lines.append("🧾 Расходы за сегодня:")
        for item in expense_items:
            lines.append(f"• {item.category.icon} {item.category.full_name}: {item.amount:.2f} — {item.description or 'без описания'}")
    return "\n".join(lines).strip()


@sync_to_async
def get_week_summary_text(user) -> str:
    return build_text_summary_for_period(user, period="week")


@sync_to_async
def get_category_report_text(user, category_name: str) -> str:
    category = Category.objects.filter(user=user, name__icontains=category_name).select_related("parent").first()
    if not category:
        return "Категория не найдена. Проверьте название и попробуйте снова."
    start_date = timezone.localdate() - timedelta(days=6)
    queryset = Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.TYPE_EXPENSE,
        category=category,
        operation_date__gte=start_date,
    )
    total = sum(item.amount for item in queryset)
    return f"{category.icon} Категория «{category.full_name}» за последние 7 дней: {total:.2f}"


@sync_to_async
def add_transaction_from_bot(user, transaction_type: str, amount: float, category_id: int, description: str, operation_date=None) -> str:
    category = Category.objects.filter(user=user, id=category_id, is_active=True).select_related("parent").first()
    if not category:
        return "Категория не найдена."
    if operation_date is None:
        operation_date = timezone.localdate()
    Transaction.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=amount,
        operation_date=operation_date,
        category=category,
        description=description,
    )
    return f"Операция сохранена: {category.icon} {category.full_name} — {amount:.2f}"


@sync_to_async
def get_categories_for_user(user) -> list[tuple[int, str]]:
    return [
        (category.id, f"{category.icon} {category.full_name}")
        for category in user.categories.filter(is_active=True).select_related("parent").order_by("parent__name", "name")
    ]


@sync_to_async
def get_compare_week_text(user) -> str:
    today = timezone.localdate()
    current_start = today - timedelta(days=6)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)
    current_total = (
        Transaction.objects.filter(
            user=user,
            transaction_type=Transaction.TYPE_EXPENSE,
            operation_date__range=(current_start, today),
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    previous_total = (
        Transaction.objects.filter(
            user=user,
            transaction_type=Transaction.TYPE_EXPENSE,
            operation_date__range=(previous_start, previous_end),
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    difference = current_total - previous_total
    if difference > 0:
        trend = f"Расходы выросли на {difference:.2f}"
    elif difference < 0:
        trend = f"Расходы снизились на {abs(difference):.2f}"
    else:
        trend = "Расходы не изменились."
    return (
        f"📈 Сравнение недель\n"
        f"• Текущая неделя: {current_total:.2f}\n"
        f"• Прошлая неделя: {previous_total:.2f}\n"
        f"• Итог: {trend}"
    )


@sync_to_async
def write_notification_history(user, notification_type: str, message: str, is_success: bool = True) -> None:
    NotificationHistory.objects.create(
        user=user,
        channel=NotificationHistory.CHANNEL_TELEGRAM,
        notification_type=notification_type,
        message=message,
        is_success=is_success,
    )


@sync_to_async
def add_transaction_from_voice_text(user, transcript: str) -> str:
    if not user.profile.telegram_voice_enabled:
        return "Голосовой ввод отключён в профиле. При желании вы можете включить эту дополнительную опцию позже."
    parsed = parse_transaction_text(transcript)
    if not parsed:
        return (
            "Не удалось надёжно распознать операцию из голосового сообщения.\n"
            "Попробуйте сказать, например:\n"
            "«расход 1250 еда 08.04.2026 продукты»\n"
            "или используйте обычное пошаговое добавление через кнопки."
        )
    raw_tail = (parsed.get("raw_tail") or "").strip()
    categories = list(user.categories.filter(is_active=True).select_related("parent"))
    matched_category = None
    for category in categories:
        if category.full_name.lower() in raw_tail or category.name.lower() in raw_tail:
            matched_category = category
            break
    if matched_category is None:
        return (
            f"Голос распознан так:\n«{transcript}»\n\n"
            "Но категорию определить не удалось. Пожалуйста, назовите категорию точнее или воспользуйтесь обычным пошаговым добавлением."
        )
    operation_date = parsed.get("operation_date") or timezone.localdate()
    description = raw_tail.replace(matched_category.full_name.lower(), "").replace(matched_category.name.lower(), "").strip()
    Transaction.objects.create(
        user=user,
        transaction_type=parsed["transaction_type"],
        amount=Decimal(parsed["amount"]).quantize(Decimal("0.01")),
        operation_date=operation_date,
        category=matched_category,
        description=description,
    )
    return (
        f"Голосовая операция сохранена.\n"
        f"• Тип: {'Доход' if parsed['transaction_type'] == Transaction.TYPE_INCOME else 'Расход'}\n"
        f"• Сумма: {Decimal(parsed['amount']).quantize(Decimal('0.01')):.2f}\n"
        f"• Категория: {matched_category.full_name}\n"
        f"• Дата: {operation_date.strftime('%d.%m.%Y')}"
    )
