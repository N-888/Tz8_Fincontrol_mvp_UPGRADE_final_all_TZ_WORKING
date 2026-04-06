# Импортируем модуль os, чтобы задать путь к настройкам Django.
import os

# Импортируем фабрику WSGI-приложения Django.
from django.core.wsgi import get_wsgi_application

# Указываем путь к настройкам проекта.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fincontrol.settings")

# Создаём WSGI-приложение для классического веб-запуска.
application = get_wsgi_application()
