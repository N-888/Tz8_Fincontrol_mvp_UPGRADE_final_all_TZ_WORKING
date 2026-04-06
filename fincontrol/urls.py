# Импортируем административный сайт Django.
from django.contrib import admin

# Импортируем встроенные представления аутентификации.
from django.contrib.auth import views as auth_views

# Импортируем функции маршрутизации.
from django.urls import include, path

# Импортируем пользовательское представление регистрации.
from core.views import register_view

# Описываем все маршруты проекта.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/register/", register_view, name="register"),
    path("", include("core.urls")),
]
