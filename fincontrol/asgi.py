# Импортируем модуль os, чтобы задать путь к настройкам Django.
import os

# Импортируем фабрику ASGI-приложения Django.
from django.core.asgi import get_asgi_application

# Указываем путь к настройкам проекта.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fincontrol.settings")

# Создаём ASGI-приложение для асинхронных серверов.
application = get_asgi_application()
