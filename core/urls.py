# Импортируем path для описания маршрутов.
from django.urls import path

# Импортируем представления приложения.
from core.views import (
    category_create_view,
    category_delete_view,
    category_list_view,
    category_update_view,
    dashboard_view,
    profile_view,
    saved_report_delete_view,
    saved_report_list_view,
    transaction_create_view,
    transaction_delete_view,
    transaction_list_view,
    transaction_update_view,
)

# Описываем маршруты приложения.
urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("transactions/", transaction_list_view, name="transaction_list"),
    path("transactions/create/", transaction_create_view, name="transaction_create"),
    path("transactions/<int:pk>/edit/", transaction_update_view, name="transaction_update"),
    path("transactions/<int:pk>/delete/", transaction_delete_view, name="transaction_delete"),
    path("categories/", category_list_view, name="category_list"),
    path("categories/create/", category_create_view, name="category_create"),
    path("categories/<int:pk>/edit/", category_update_view, name="category_update"),
    path("categories/<int:pk>/delete/", category_delete_view, name="category_delete"),
    path("profile/", profile_view, name="profile"),
    path("reports/", saved_report_list_view, name="saved_report_list"),
    path("reports/<int:pk>/delete/", saved_report_delete_view, name="saved_report_delete"),
]
