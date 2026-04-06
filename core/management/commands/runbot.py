# Импортируем базовый класс команд Django.
from django.core.management.base import BaseCommand

# Импортируем функцию запуска Telegram-бота.
from core.telegram_bot.bot import run_bot


class Command(BaseCommand):
    # Задаём человекочитаемое описание команды.
    help = "Запускает Telegram-бота FinControl"

    def handle(self, *args, **options):
        # Пишем сообщение о старте бота в консоль.
        self.stdout.write(self.style.SUCCESS("Telegram-бот запускается..."))

        # Запускаем бота.
        run_bot()
