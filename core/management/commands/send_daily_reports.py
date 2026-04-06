# Импортируем asyncio для запуска асинхронной отправки отчётов.
import asyncio

# Импортируем Bot aiogram.
from aiogram import Bot

# Импортируем режим HTML.
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импортируем sync_to_async, чтобы безопасно обращаться к Django ORM из async-кода.
from asgiref.sync import sync_to_async

# Импортируем настройки Django.
from django.conf import settings

# Импортируем базовую команду Django.
from django.core.management.base import BaseCommand

# Импортируем профили пользователей.
from core.models import UserProfile

# Импортируем аналитику и историю уведомлений.
from core.services.analytics import build_text_summary_for_period
from core.services.telegram_helpers import write_notification_history


@sync_to_async
def get_daily_profiles():
    # Берём только профили с Telegram ID и включёнными ежедневными отчётами.
    return list(UserProfile.objects.filter(telegram_id__isnull=False, daily_reports_enabled=True).select_related("user"))


@sync_to_async
def get_summary_text_for_user(user):
    # Формируем текст сводки за день для конкретного пользователя.
    return build_text_summary_for_period(user, period="day")


class Command(BaseCommand):
    # Описываем назначение команды.
    help = "Отправляет ежедневные Telegram-отчёты пользователям, у которых включены уведомления"

    async def send_reports(self) -> None:
        # Проверяем наличие токена бота.
        if not settings.TELEGRAM_BOT_TOKEN:
            raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в файле .env")

        # Создаём объект бота.
        bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        # Получаем список профилей через безопасную синхронную обёртку.
        profiles = await get_daily_profiles()

        # Проходим по каждому профилю.
        for profile in profiles:
            # Формируем текст сводки.
            summary_text = await get_summary_text_for_user(profile.user)

            # Пытаемся отправить сообщение.
            try:
                # Отправляем сообщение пользователю в Telegram.
                await bot.send_message(chat_id=profile.telegram_id, text=summary_text)

                # Записываем успешную отправку в историю.
                await write_notification_history(profile.user, "daily_report", summary_text, True)
            except Exception as error:
                # Записываем неуспешную отправку в историю.
                await write_notification_history(profile.user, "daily_report", str(error), False)

        # Закрываем сессию бота.
        await bot.session.close()

    def handle(self, *args, **options):
        # Пишем сообщение о начале отправки.
        self.stdout.write(self.style.SUCCESS("Запущена отправка ежедневных отчётов..."))

        # Запускаем асинхронную логику отправки.
        asyncio.run(self.send_reports())

        # Пишем сообщение об окончании.
        self.stdout.write(self.style.SUCCESS("Отправка ежедневных отчётов завершена."))
