# Импортируем AppConfig, чтобы настроить приложение Django.
from django.apps import AppConfig


class CoreConfig(AppConfig):
    # Указываем тип автоматически создаваемого первичного ключа.
    default_auto_field = "django.db.models.BigAutoField"

    # Указываем техническое имя приложения.
    name = "core"

    def ready(self) -> None:
        # Импортируем сигналы при готовности приложения.
        import core.signals  # noqa: F401
