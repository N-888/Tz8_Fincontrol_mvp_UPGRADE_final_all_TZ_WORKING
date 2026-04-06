#!/usr/bin/env python
# Импортируем модуль os, чтобы работать с переменными окружения.
import os

# Импортируем модуль sys, чтобы передать аргументы командной строки в Django.
import sys


def main() -> None:
    # Указываем Django, где находится файл настроек проекта.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fincontrol.settings")

    # Пытаемся импортировать функцию запуска административных команд Django.
    from django.core.management import execute_from_command_line

    # Передаём управление стандартному механизму команд Django.
    execute_from_command_line(sys.argv)


# Проверяем, что файл запущен как основной скрипт.
if __name__ == "__main__":
    # Запускаем главную функцию.
    main()
