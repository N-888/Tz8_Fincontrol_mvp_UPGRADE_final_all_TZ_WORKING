# Импортируем os, чтобы читать переменные окружения.
import os

# Импортируем Path, чтобы удобно собирать пути к файлам и папкам.
from pathlib import Path

# Импортируем load_dotenv, чтобы автоматически подгружать переменные из файла .env.
from dotenv import load_dotenv

# Вычисляем корневую папку проекта.
BASE_DIR = Path(__file__).resolve().parent.parent

# Подгружаем переменные окружения из файла .env, если он существует.
load_dotenv(BASE_DIR / ".env")

# Читаем секретный ключ из переменных окружения.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")

# Читаем флаг отладки из переменных окружения.
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

# Читаем список хостов и превращаем строку в список.
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

# Перечисляем стандартные приложения Django.
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Перечисляем локальные приложения проекта.
LOCAL_APPS = [
    "core.apps.CoreConfig",
]

# Собираем финальный список приложений.
INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

# Описываем middleware-слой Django.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Указываем корневой файл маршрутов.
ROOT_URLCONF = "fincontrol.urls"

# Описываем шаблонизатор Django.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Указываем путь к WSGI-приложению.
WSGI_APPLICATION = "fincontrol.wsgi.application"

# Настраиваем базу данных SQLite для MVP.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Настраиваем валидаторы паролей Django.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Указываем язык интерфейса.
LANGUAGE_CODE = "ru-ru"

# Указываем часовой пояс.
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Europe/Moscow")

# Разрешаем хранить время с часовыми поясами.
USE_TZ = True

# Разрешаем интернационализацию.
USE_I18N = True

# Указываем URL для статических файлов.
STATIC_URL = "static/"

# Указываем дополнительные папки со статикой.
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Указываем папку для команды collectstatic.
STATIC_ROOT = BASE_DIR / "staticfiles"

# Указываем тип первичных ключей по умолчанию.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Указываем URL входа.
LOGIN_URL = "login"

# Указываем URL после входа.
LOGIN_REDIRECT_URL = "dashboard"

# Указываем URL после выхода.
LOGOUT_REDIRECT_URL = "login"

# Включаем безопасную длину заголовков сообщений.
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Читаем токен Telegram-бота.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Указываем имя проекта для шаблонов и сервисов.
PROJECT_NAME = "FinControl"
