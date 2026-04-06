# Импортируем datetime для преобразования строк в даты.
from datetime import datetime

# Импортируем сообщения Django.
from django.contrib import messages

# Импортируем декоратор входа.
from django.contrib.auth.decorators import login_required

# Импортируем функцию входа пользователя после регистрации.
from django.contrib.auth import login

# Импортируем HTTP-ответ перенаправления.
from django.http import HttpRequest, HttpResponse

# Импортируем функции получения объекта и рендера шаблонов.
from django.shortcuts import get_object_or_404, redirect, render

# Импортируем timezone для работы с датами.
from django.utils import timezone

# Импортируем локальные формы.
from core.forms import CategoryForm, ProfileForm, RegisterForm, SavedReportForm, TransactionForm

# Импортируем локальные модели.
from core.models import Category, SavedReport, Transaction

# Импортируем аналитику.
from core.services.analytics import build_dashboard_data


def register_view(request: HttpRequest) -> HttpResponse:
    # Проверяем, что отправлена POST-форма.
    if request.method == "POST":
        # Заполняем форму данными пользователя.
        form = RegisterForm(request.POST)

        # Если форма валидна, сохраняем пользователя.
        if form.is_valid():
            user = form.save()

            # Выполняем автоматический вход после регистрации.
            login(request, user)

            # Показываем успешное сообщение.
            messages.success(request, "Регистрация прошла успешно. Добро пожаловать в FinControl!")

            # Перенаправляем пользователя на главную страницу кабинета.
            return redirect("dashboard")
    else:
        # Если запрос GET, создаём пустую форму.
        form = RegisterForm()

    # Рендерим страницу регистрации.
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    # Получаем выбранный период из query-параметров.
    period = request.GET.get("period", "month")

    # Получаем выбранную категорию из query-параметров.
    category_id = request.GET.get("category") or None

    # Получаем строки дат из query-параметров.
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    # Инициализируем даты значением None.
    start_date = None
    end_date = None

    # Если дата начала передана, преобразуем строку в дату.
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    # Если дата окончания передана, преобразуем строку в дату.
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    # Строим набор данных для дашборда.
    data = build_dashboard_data(
        user=request.user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    # Создаём форму сохранения отчёта.
    saved_report_form = SavedReportForm(
        user=request.user,
        initial={
            "period": "custom" if start_date and end_date else period,
            "start_date": start_date,
            "end_date": end_date,
            "category": category_id,
        },
    )

    # Добавляем вспомогательные данные в контекст.
    data["categories"] = request.user.categories.filter(is_active=True)
    data["saved_report_form"] = saved_report_form

    # Рендерим страницу дашборда.
    return render(request, "core/dashboard.html", data)


@login_required
def transaction_list_view(request: HttpRequest) -> HttpResponse:
    # Получаем список операций текущего пользователя.
    queryset = Transaction.objects.filter(user=request.user).select_related("category")

    # Получаем фильтр типа операции.
    transaction_type = request.GET.get("type")

    # Получаем фильтр категории.
    category_id = request.GET.get("category")

    # Получаем фильтр даты начала.
    start_date = request.GET.get("start_date")

    # Получаем фильтр даты конца.
    end_date = request.GET.get("end_date")

    # Если выбран тип операции, фильтруем по нему.
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)

    # Если выбрана категория, фильтруем по ней.
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # Если выбрана дата начала, фильтруем по нижней границе.
    if start_date:
        queryset = queryset.filter(operation_date__gte=start_date)

    # Если выбрана дата конца, фильтруем по верхней границе.
    if end_date:
        queryset = queryset.filter(operation_date__lte=end_date)

    # Формируем контекст страницы.
    context = {
        "transactions": queryset,
        "categories": request.user.categories.filter(is_active=True),
    }

    # Рендерим страницу истории операций.
    return render(request, "core/transaction_list.html", context)


@login_required
def transaction_create_view(request: HttpRequest) -> HttpResponse:
    # Проверяем метод запроса.
    if request.method == "POST":
        # Заполняем форму POST-данными.
        form = TransactionForm(request.POST, user=request.user)

        # Если форма валидна, сохраняем операцию.
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, "Операция успешно добавлена.")
            return redirect("transaction_list")
    else:
        # Если запрос GET, создаём пустую форму.
        form = TransactionForm(user=request.user)

    # Рендерим страницу формы операции.
    return render(request, "core/transaction_form.html", {"form": form, "title": "Новая операция"})


@login_required
def transaction_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем операцию текущего пользователя или 404.
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    # Проверяем метод запроса.
    if request.method == "POST":
        # Заполняем форму текущим объектом и новыми данными.
        form = TransactionForm(request.POST, instance=transaction, user=request.user)

        # Если форма валидна, сохраняем изменения.
        if form.is_valid():
            form.save()
            messages.success(request, "Операция успешно обновлена.")
            return redirect("transaction_list")
    else:
        # Если запрос GET, показываем форму редактирования.
        form = TransactionForm(instance=transaction, user=request.user)

    # Рендерим страницу редактирования.
    return render(request, "core/transaction_form.html", {"form": form, "title": "Редактирование операции"})


@login_required
def transaction_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем операцию текущего пользователя или 404.
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    # Если запрос POST, удаляем запись.
    if request.method == "POST":
        transaction.delete()
        messages.success(request, "Операция удалена.")
        return redirect("transaction_list")

    # Рендерим универсальное окно подтверждения.
    return render(
        request,
        "core/confirm_delete.html",
        {"title": "Удаление операции", "object_name": str(transaction)},
    )


@login_required
def category_list_view(request: HttpRequest) -> HttpResponse:
    # Получаем категории текущего пользователя.
    categories = request.user.categories.all()

    # Рендерим страницу списка категорий.
    return render(request, "core/category_list.html", {"categories": categories})


@login_required
def category_create_view(request: HttpRequest) -> HttpResponse:
    # Проверяем метод запроса.
    if request.method == "POST":
        # Заполняем форму POST-данными.
        form = CategoryForm(request.POST)

        # Если форма валидна, сохраняем категорию.
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, "Категория успешно создана.")
            return redirect("category_list")
    else:
        # Если запрос GET, создаём пустую форму.
        form = CategoryForm()

    # Рендерим страницу формы категории.
    return render(request, "core/category_form.html", {"form": form, "title": "Новая категория"})


@login_required
def category_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем категорию текущего пользователя или 404.
    category = get_object_or_404(Category, pk=pk, user=request.user)

    # Проверяем метод запроса.
    if request.method == "POST":
        # Заполняем форму текущим объектом и новыми данными.
        form = CategoryForm(request.POST, instance=category)

        # Если форма валидна, сохраняем изменения.
        if form.is_valid():
            form.save()
            messages.success(request, "Категория успешно обновлена.")
            return redirect("category_list")
    else:
        # Если запрос GET, показываем форму редактирования.
        form = CategoryForm(instance=category)

    # Рендерим страницу формы категории.
    return render(request, "core/category_form.html", {"form": form, "title": "Редактирование категории"})


@login_required
def category_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем категорию текущего пользователя или 404.
    category = get_object_or_404(Category, pk=pk, user=request.user)

    # Если запрос POST, удаляем категорию.
    if request.method == "POST":
        category.delete()
        messages.success(request, "Категория удалена.")
        return redirect("category_list")

    # Рендерим окно подтверждения удаления.
    return render(
        request,
        "core/confirm_delete.html",
        {"title": "Удаление категории", "object_name": str(category)},
    )


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    # Получаем профиль текущего пользователя.
    profile = request.user.profile

    # Если пользователь нажал кнопку обновления Telegram-кода.
    if request.method == "POST" and request.POST.get("action") == "regenerate_code":
        profile.regenerate_telegram_code()
        messages.success(request, "Новый код привязки Telegram успешно создан.")
        return redirect("profile")

    # Если отправлена обычная форма профиля.
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)

        # Если форма валидна, сохраняем профиль.
        if form.is_valid():
            form.save()
            messages.success(request, "Настройки профиля сохранены.")
            return redirect("profile")
    else:
        # Если запрос GET, показываем текущие настройки.
        form = ProfileForm(instance=profile)

    # Рендерим страницу профиля.
    return render(request, "core/profile.html", {"form": form, "profile": profile})


@login_required
def saved_report_list_view(request: HttpRequest) -> HttpResponse:
    # Получаем все сохранённые отчёты текущего пользователя.
    reports = request.user.saved_reports.select_related("category").all()

    # Если отправлена форма нового отчёта.
    if request.method == "POST":
        form = SavedReportForm(request.POST, user=request.user)

        # Если форма валидна, сохраняем отчёт.
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()
            messages.success(request, "Отчёт сохранён в избранное.")
            return redirect("saved_report_list")
    else:
        # Если запрос GET, показываем пустую форму.
        form = SavedReportForm(user=request.user)

    # Рендерим страницу сохранённых отчётов.
    return render(request, "core/saved_report_list.html", {"reports": reports, "form": form})


@login_required
def saved_report_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем сохранённый отчёт текущего пользователя.
    report = get_object_or_404(SavedReport, pk=pk, user=request.user)

    # Если подтверждено удаление, удаляем отчёт.
    if request.method == "POST":
        report.delete()
        messages.success(request, "Сохранённый отчёт удалён.")
        return redirect("saved_report_list")

    # Рендерим окно подтверждения удаления.
    return render(
        request,
        "core/confirm_delete.html",
        {"title": "Удаление отчёта", "object_name": report.name},
    )
