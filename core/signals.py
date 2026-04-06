# Импортируем модель пользователя Django.
from django.contrib.auth.models import User

# Импортируем сигнал сохранения модели.
from django.db.models.signals import post_save

# Импортируем декоратор приёмника сигнала.
from django.dispatch import receiver

# Импортируем локальные модели.
from core.models import Category, UserProfile

# Описываем стартовый набор категорий для новых пользователей.
DEFAULT_CATEGORIES = [
    ("Еда", "🍔"),
    ("Транспорт", "🚌"),
    ("Развлечения", "🎬"),
    ("Зарплата", "💳"),
    ("Фриланс", "💼"),
]


@receiver(post_save, sender=User)
def create_profile_and_categories(sender, instance, created, **kwargs):
    # Проверяем, был ли пользователь создан впервые.
    if not created:
        # Прерываем выполнение, если это обычное обновление пользователя.
        return

    # Создаём профиль для нового пользователя.
    UserProfile.objects.create(user=instance)

    # Проходим по списку стандартных категорий.
    for name, icon in DEFAULT_CATEGORIES:
        # Создаём категории для нового пользователя.
        Category.objects.create(user=instance, name=name, icon=icon)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    # Проверяем наличие связанного профиля.
    if hasattr(instance, "profile"):
        # Сохраняем профиль, если он существует.
        instance.profile.save()
