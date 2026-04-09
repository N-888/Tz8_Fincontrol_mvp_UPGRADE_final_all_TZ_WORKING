# Импортируем datetime, чтобы преобразовывать строки фильтров в даты.
from datetime import datetime

# Импортируем Path, чтобы обращаться к системным шрифтам Windows по полному пути.
from pathlib import Path

# Импортируем сообщения Django для уведомления пользователя об успешных действиях.
from django.contrib import messages

# Импортируем декоратор, чтобы ограничивать доступ к страницам только авторизованным пользователям.
from django.contrib.auth.decorators import login_required

# Импортируем функцию логина, чтобы сразу входить после регистрации.
from django.contrib.auth import login

# Импортируем HTTP-ответы Django.
from django.http import HttpRequest, HttpResponse

# Импортируем вспомогательные функции для получения объектов, перенаправления и рендера шаблонов.
from django.shortcuts import get_object_or_404, redirect, render

# Импортируем timezone, чтобы работать с локальным временем проекта.
from django.utils import timezone

# Импортируем Workbook, чтобы формировать Excel-файлы.
from openpyxl import Workbook

# Импортируем размер страницы A4 для PDF.
from reportlab.lib.pagesizes import A4

# Импортируем canvas для прямой генерации PDF-файла.
from reportlab.pdfgen import canvas

# Импортируем pdfmetrics, чтобы регистрировать кириллические шрифты.
from reportlab.pdfbase import pdfmetrics

# Импортируем TTFont, чтобы подключать обычные TTF-шрифты Windows.
from reportlab.pdfbase.ttfonts import TTFont

# Импортируем формы приложения.
from core.forms import CategoryForm, ProfileForm, RegisterForm, SavedReportForm, TransactionForm

# Импортируем модели приложения.
from core.models import Category, SavedReport, Transaction

# Импортируем сервис аналитики и сервис получения отфильтрованных операций.
from core.services.analytics import build_dashboard_data, get_filtered_transactions


# Создаём представление регистрации нового пользователя.
def register_view(request: HttpRequest) -> HttpResponse:
    # Проверяем, отправлена ли форма методом POST.
    if request.method == "POST":
        # Создаём форму регистрации и заполняем её данными из запроса.
        form = RegisterForm(request.POST)

        # Проверяем, прошла ли форма валидацию.
        if form.is_valid():
            # Сохраняем нового пользователя.
            user = form.save()

            # Выполняем автоматический вход пользователя после регистрации.
            login(request, user)

            # Показываем сообщение об успешной регистрации.
            messages.success(request, "Регистрация прошла успешно. Добро пожаловать в FinControl!")

            # Перенаправляем пользователя на главную страницу дашборда.
            return redirect("dashboard")
    else:
        # Если запрос не POST, создаём пустую форму регистрации.
        form = RegisterForm()

    # Отображаем страницу регистрации.
    return render(request, "registration/register.html", {"form": form})


# Ограничиваем доступ к дашборду только авторизованным пользователям.
@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    # Получаем выбранный период из строки запроса.
    period = request.GET.get("period", "month")

    # Получаем выбранную категорию из строки запроса.
    category_id = request.GET.get("category") or None

    # Получаем текст даты начала.
    start_date_str = request.GET.get("start_date")

    # Получаем текст даты конца.
    end_date_str = request.GET.get("end_date")

    # Инициализируем дату начала пустым значением.
    start_date = None

    # Инициализируем дату конца пустым значением.
    end_date = None

    # Если дата начала передана, преобразуем её в объект date.
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    # Если дата конца передана, преобразуем её в объект date.
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    # Строим аналитические данные для дашборда.
    data = build_dashboard_data(
        user=request.user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    # Создаём форму сохранения отчёта в избранное.
    saved_report_form = SavedReportForm(
        user=request.user,
        initial={
            "period": "custom" if start_date and end_date else period,
            "start_date": start_date,
            "end_date": end_date,
            "category": category_id,
        },
    )

    # Добавляем список категорий в контекст шаблона.
    data["categories"] = request.user.categories.filter(is_active=True).select_related("parent")

    # Добавляем форму сохранения отчёта в контекст шаблона.
    data["saved_report_form"] = saved_report_form

    # Отображаем страницу дашборда.
    return render(request, "core/dashboard.html", data)


# Ограничиваем доступ к списку операций только авторизованным пользователям.
@login_required
def transaction_list_view(request: HttpRequest) -> HttpResponse:
    # Получаем все операции текущего пользователя.
    queryset = Transaction.objects.filter(user=request.user).select_related("category", "category__parent")

    # Получаем фильтр по типу операции.
    transaction_type = request.GET.get("type")

    # Получаем фильтр по категории.
    category_id = request.GET.get("category")

    # Получаем фильтр по дате начала.
    start_date = request.GET.get("start_date")

    # Получаем фильтр по дате конца.
    end_date = request.GET.get("end_date")

    # Если фильтр типа операции задан, применяем его.
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)

    # Если фильтр категории задан, применяем его.
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # Если дата начала задана, фильтруем операции снизу по диапазону.
    if start_date:
        queryset = queryset.filter(operation_date__gte=start_date)

    # Если дата конца задана, фильтруем операции сверху по диапазону.
    if end_date:
        queryset = queryset.filter(operation_date__lte=end_date)

    # Формируем контекст страницы списка операций.
    context = {
        "transactions": queryset,
        "categories": request.user.categories.filter(is_active=True).select_related("parent"),
    }

    # Отображаем страницу списка операций.
    return render(request, "core/transaction_list.html", context)


# Ограничиваем доступ к созданию операции только авторизованным пользователям.
@login_required
def transaction_create_view(request: HttpRequest) -> HttpResponse:
    # Проверяем, отправлена ли форма методом POST.
    if request.method == "POST":
        # Создаём форму операции и передаём текущего пользователя.
        form = TransactionForm(request.POST, user=request.user)

        # Проверяем валидность формы.
        if form.is_valid():
            # Создаём объект операции без немедленного сохранения.
            transaction = form.save(commit=False)

            # Назначаем операции текущего пользователя.
            transaction.user = request.user

            # Сохраняем операцию в базу данных.
            transaction.save()

            # Показываем сообщение об успешном добавлении.
            messages.success(request, "Операция успешно добавлена.")

            # Перенаправляем на список операций.
            return redirect("transaction_list")
    else:
        # Если это GET-запрос, создаём пустую форму операции.
        form = TransactionForm(user=request.user)

    # Отображаем страницу создания новой операции.
    return render(request, "core/transaction_form.html", {"form": form, "title": "Новая операция"})


# Ограничиваем доступ к редактированию операции только авторизованным пользователям.
@login_required
def transaction_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем операцию текущего пользователя или ошибку 404.
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    # Проверяем, отправлена ли форма методом POST.
    if request.method == "POST":
        # Создаём форму редактирования операции.
        form = TransactionForm(request.POST, instance=transaction, user=request.user)

        # Проверяем валидность формы.
        if form.is_valid():
            # Сохраняем изменения операции.
            form.save()

            # Показываем сообщение об успешном обновлении.
            messages.success(request, "Операция успешно обновлена.")

            # Перенаправляем пользователя на список операций.
            return redirect("transaction_list")
    else:
        # Если это GET-запрос, создаём форму с текущими данными операции.
        form = TransactionForm(instance=transaction, user=request.user)

    # Отображаем страницу редактирования операции.
    return render(request, "core/transaction_form.html", {"form": form, "title": "Редактирование операции"})


# Ограничиваем доступ к удалению операции только авторизованным пользователям.
@login_required
def transaction_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем операцию текущего пользователя или ошибку 404.
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    # Если отправлено подтверждение удаления, удаляем операцию.
    if request.method == "POST":
        # Удаляем операцию.
        transaction.delete()

        # Показываем сообщение об успешном удалении.
        messages.success(request, "Операция удалена.")

        # Перенаправляем пользователя на список операций.
        return redirect("transaction_list")

    # Отображаем страницу подтверждения удаления.
    return render(
        request,
        "core/confirm_delete.html",
        {"title": "Удаление операции", "object_name": str(transaction)},
    )


# Ограничиваем доступ к списку категорий только авторизованным пользователям.
@login_required
def category_list_view(request: HttpRequest) -> HttpResponse:
    # Получаем все категории и подкатегории пользователя.
    categories = request.user.categories.select_related("parent").all()

    # Формируем список корневых категорий без родителя.
    root_categories = [item for item in categories if item.parent_id is None]

    # Отображаем страницу списка категорий.
    return render(
        request,
        "core/category_list.html",
        {
            "categories": categories,
            "root_categories": root_categories,
        },
    )


# Ограничиваем доступ к созданию категории только авторизованным пользователям.
@login_required
def category_create_view(request: HttpRequest) -> HttpResponse:
    # Проверяем, отправлена ли форма методом POST.
    if request.method == "POST":
        # Создаём форму категории и передаём пользователя.
        form = CategoryForm(request.POST, user=request.user)

        # Проверяем валидность формы.
        if form.is_valid():
            # Создаём категорию без немедленного сохранения.
            category = form.save(commit=False)

            # Назначаем пользователя владельцем категории.
            category.user = request.user

            # Сохраняем категорию.
            category.save()

            # Показываем сообщение об успешном создании.
            messages.success(request, "Категория успешно создана.")

            # Перенаправляем на список категорий.
            return redirect("category_list")
    else:
        # Если это GET-запрос, создаём пустую форму категории.
        form = CategoryForm(user=request.user)

    # Отображаем страницу создания категории.
    return render(request, "core/category_form.html", {"form": form, "title": "Новая категория"})


# Ограничиваем доступ к редактированию категории только авторизованным пользователям.
@login_required
def category_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем категорию текущего пользователя или ошибку 404.
    category = get_object_or_404(Category, pk=pk, user=request.user)

    # Проверяем, отправлена ли форма методом POST.
    if request.method == "POST":
        # Создаём форму редактирования категории.
        form = CategoryForm(request.POST, instance=category, user=request.user)

        # Проверяем валидность формы.
        if form.is_valid():
            # Сохраняем изменения категории.
            form.save()

            # Показываем сообщение об успешном обновлении.
            messages.success(request, "Категория успешно обновлена.")

            # Перенаправляем на список категорий.
            return redirect("category_list")
    else:
        # Если это GET-запрос, создаём форму с текущими данными категории.
        form = CategoryForm(instance=category, user=request.user)

    # Отображаем страницу редактирования категории.
    return render(request, "core/category_form.html", {"form": form, "title": "Редактирование категории"})


# Ограничиваем доступ к удалению категории только авторизованным пользователям.
@login_required
def category_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем категорию текущего пользователя или ошибку 404.
    category = get_object_or_404(Category, pk=pk, user=request.user)

    # Если отправлено подтверждение удаления, удаляем категорию.
    if request.method == "POST":
        # Удаляем категорию.
        category.delete()

        # Показываем сообщение об успешном удалении.
        messages.success(request, "Категория удалена.")

        # Перенаправляем на список категорий.
        return redirect("category_list")

    # Отображаем страницу подтверждения удаления категории.
    return render(
        request,
        "core/confirm_delete.html",
        {"title": "Удаление категории", "object_name": str(category)},
    )


# Ограничиваем доступ к профилю только авторизованным пользователям.
@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    # Получаем профиль текущего пользователя.
    profile = request.user.profile

    # Если пользователь запросил новый Telegram-код, обрабатываем это отдельно.
    if request.method == "POST" and request.POST.get("action") == "regenerate_code":
        # Генерируем новый код привязки Telegram.
        profile.regenerate_telegram_code()

        # Показываем сообщение об успешной генерации.
        messages.success(request, "Новый код привязки Telegram успешно создан.")

        # Перенаправляем обратно на профиль.
        return redirect("profile")

    # Если отправлена обычная форма настроек профиля.
    if request.method == "POST":
        # Создаём форму профиля с данными POST.
        form = ProfileForm(request.POST, instance=profile)

        # Проверяем валидность формы.
        if form.is_valid():
            # Сохраняем настройки профиля.
            form.save()

            # Показываем сообщение об успешном сохранении.
            messages.success(request, "Настройки профиля сохранены.")

            # Перенаправляем обратно на профиль.
            return redirect("profile")
    else:
        # Если это GET-запрос, создаём форму с текущими значениями профиля.
        form = ProfileForm(instance=profile)

    # Отображаем страницу профиля.
    return render(request, "core/profile.html", {"form": form, "profile": profile})


# Ограничиваем доступ к списку сохранённых отчётов только авторизованным пользователям.
@login_required
def saved_report_list_view(request: HttpRequest) -> HttpResponse:
    # Получаем все сохранённые отчёты пользователя.
    reports = request.user.saved_reports.select_related("category", "category__parent").all()

    # Если отправлена форма нового отчёта, обрабатываем её.
    if request.method == "POST":
        # Создаём форму сохранённого отчёта.
        form = SavedReportForm(request.POST, user=request.user)

        # Проверяем валидность формы.
        if form.is_valid():
            # Создаём объект отчёта без немедленного сохранения.
            report = form.save(commit=False)

            # Назначаем отчёту текущего пользователя.
            report.user = request.user

            # Сохраняем отчёт в базу.
            report.save()

            # Показываем сообщение об успешном сохранении.
            messages.success(request, "Отчёт сохранён в избранное.")

            # Перенаправляем на страницу сохранённых отчётов.
            return redirect("saved_report_list")
    else:
        # Если это GET-запрос, создаём пустую форму сохранённого отчёта.
        form = SavedReportForm(user=request.user)

    # Отображаем страницу сохранённых отчётов.
    return render(request, "core/saved_report_list.html", {"reports": reports, "form": form})


# Ограничиваем доступ к удалению сохранённого отчёта только авторизованным пользователям.
@login_required
def saved_report_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    # Получаем сохранённый отчёт текущего пользователя или ошибку 404.
    report = get_object_or_404(SavedReport, pk=pk, user=request.user)

    # Если отправлено подтверждение удаления, удаляем отчёт.
    if request.method == "POST":
        # Удаляем отчёт.
        report.delete()

        # Показываем сообщение об успешном удалении.
        messages.success(request, "Сохранённый отчёт удалён.")

        # Перенаправляем на список сохранённых отчётов.
        return redirect("saved_report_list")

    # Отображаем страницу подтверждения удаления отчёта.
    return render(
        request,
        "core/confirm_delete.html",
        {"title": "Удаление отчёта", "object_name": report.name},
    )


# Ограничиваем доступ к Excel-экспорту только авторизованным пользователям.
@login_required
def export_report_excel_view(request: HttpRequest) -> HttpResponse:
    # Получаем выбранный период из строки запроса.
    period = request.GET.get("period", "month")

    # Получаем выбранную категорию из строки запроса.
    category_id = request.GET.get("category") or None

    # Получаем строку даты начала.
    start_date_str = request.GET.get("start_date")

    # Получаем строку даты конца.
    end_date_str = request.GET.get("end_date")

    # Если дата начала передана, преобразуем её в объект date.
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None

    # Если дата конца передана, преобразуем её в объект date.
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

    # Получаем отфильтрованные операции по текущим параметрам.
    queryset = get_filtered_transactions(
        user=request.user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    # Получаем аналитическую сводку по текущему фильтру.
    dashboard_data = build_dashboard_data(
        user=request.user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    # Создаём новую Excel-книгу.
    workbook = Workbook()

    # Получаем активный лист книги.
    sheet = workbook.active

    # Переименовываем лист в понятное имя.
    sheet.title = "Отчёт"

    # Записываем шапку Excel-отчёта.
    sheet["A1"] = "Финансовый отчёт FinControl"
    sheet["A2"] = "Период"
    sheet["B2"] = period
    sheet["A3"] = "Доходы"
    sheet["B3"] = float(dashboard_data["summary"]["income_sum"])
    sheet["A4"] = "Расходы"
    sheet["B4"] = float(dashboard_data["summary"]["expense_sum"])
    sheet["A5"] = "Баланс"
    sheet["B5"] = float(dashboard_data["summary"]["balance"])

    # Записываем заголовки таблицы операций.
    sheet["A7"] = "Дата"
    sheet["B7"] = "Тип"
    sheet["C7"] = "Категория"
    sheet["D7"] = "Сумма"
    sheet["E7"] = "Описание"

    # Начинаем заполнять строки таблицы с восьмой строки.
    row_index = 8

    # Проходим по всем операциям.
    for item in queryset:
        # Записываем дату операции.
        sheet[f"A{row_index}"] = item.operation_date.strftime("%Y-%m-%d")

        # Записываем человекочитаемый тип операции.
        sheet[f"B{row_index}"] = item.get_transaction_type_display()

        # Записываем полное имя категории.
        sheet[f"C{row_index}"] = item.category.full_name

        # Записываем сумму операции.
        sheet[f"D{row_index}"] = float(item.amount)

        # Записываем описание операции.
        sheet[f"E{row_index}"] = item.description

        # Переходим к следующей строке.
        row_index += 1

    # Создаём HTTP-ответ для скачивания Excel-файла.
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Назначаем имя скачиваемому файлу.
    response["Content-Disposition"] = 'attachment; filename="fincontrol_report.xlsx"'

    # Сохраняем Excel-книгу прямо в HTTP-ответ.
    workbook.save(response)

    # Возвращаем готовый Excel-файл.
    return response


# Создаём функцию регистрации кириллических шрифтов для PDF через ReportLab.
def register_reportlab_cyrillic_fonts() -> None:
    # Указываем путь к обычному системному шрифту Arial в Windows.
    regular_font_path = Path("C:/Windows/Fonts/arial.ttf")

    # Указываем путь к жирному системному шрифту Arial Bold в Windows.
    bold_font_path = Path("C:/Windows/Fonts/arialbd.ttf")

    # Если обычный шрифт ещё не зарегистрирован и файл существует, регистрируем его.
    if "ArialCyr" not in pdfmetrics.getRegisteredFontNames() and regular_font_path.exists():
        # Регистрируем обычный Arial под именем ArialCyr.
        pdfmetrics.registerFont(TTFont("ArialCyr", str(regular_font_path)))

    # Если жирный шрифт ещё не зарегистрирован и файл существует, регистрируем его.
    if "ArialCyrBold" not in pdfmetrics.getRegisteredFontNames() and bold_font_path.exists():
        # Регистрируем Arial Bold под именем ArialCyrBold.
        pdfmetrics.registerFont(TTFont("ArialCyrBold", str(bold_font_path)))


# Ограничиваем доступ к PDF-экспорту только авторизованным пользователям.
@login_required
def export_report_pdf_view(request: HttpRequest) -> HttpResponse:
    # Регистрируем кириллические шрифты для PDF.
    register_reportlab_cyrillic_fonts()

    # Получаем выбранный период из строки запроса.
    period = request.GET.get("period", "month")

    # Получаем выбранную категорию из строки запроса.
    category_id = request.GET.get("category") or None

    # Получаем строку даты начала.
    start_date_str = request.GET.get("start_date")

    # Получаем строку даты конца.
    end_date_str = request.GET.get("end_date")

    # Если дата начала передана, преобразуем её в объект date.
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None

    # Если дата конца передана, преобразуем её в объект date.
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

    # Получаем операции по текущему фильтру.
    queryset = get_filtered_transactions(
        user=request.user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    ).select_related("category", "category__parent")

    # Получаем итоговую аналитику для шапки PDF.
    dashboard_data = build_dashboard_data(
        user=request.user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    # Создаём HTTP-ответ с типом PDF-файла.
    response = HttpResponse(content_type="application/pdf")

    # Назначаем имя скачиваемому PDF-файлу.
    response["Content-Disposition"] = 'attachment; filename="fincontrol_report.pdf"'

    # Создаём PDF-холст формата A4.
    pdf = canvas.Canvas(response, pagesize=A4)

    # Получаем высоту страницы.
    page_height = A4[1]

    # Устанавливаем начальную вертикальную координату.
    y = page_height - 50

    # Включаем жирный кириллический шрифт для заголовка.
    pdf.setFont("ArialCyrBold", 20)

    # Печатаем главный заголовок отчёта.
    pdf.drawString(40, y, "FinControl — финансовый отчёт")

    # Смещаемся ниже.
    y -= 30

    # Включаем обычный кириллический шрифт.
    pdf.setFont("ArialCyr", 11)

    # Печатаем период отчёта.
    pdf.drawString(40, y, f"Период: {period}")

    # Смещаемся ниже.
    y -= 18

    # Печатаем время формирования отчёта.
    pdf.drawString(40, y, f"Сформировано: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}")

    # Смещаемся ниже перед блоком итогов.
    y -= 35

    # Включаем жирный шрифт для заголовка блока итогов.
    pdf.setFont("ArialCyrBold", 14)

    # Печатаем заголовок блока итогов.
    pdf.drawString(40, y, "Итоги")

    # Смещаемся ниже.
    y -= 22

    # Включаем обычный шрифт для текста итогов.
    pdf.setFont("ArialCyr", 11)

    # Формируем строку доходов.
    income_text = f"Доходы: {dashboard_data['summary']['income_sum']:.2f}".replace(".", ",")

    # Формируем строку расходов.
    expense_text = f"Расходы: {dashboard_data['summary']['expense_sum']:.2f}".replace(".", ",")

    # Формируем строку баланса.
    balance_text = f"Баланс: {dashboard_data['summary']['balance']:.2f}".replace(".", ",")

    # Печатаем строку доходов.
    pdf.drawString(40, y, income_text)

    # Смещаемся ниже.
    y -= 18

    # Печатаем строку расходов.
    pdf.drawString(40, y, expense_text)

    # Смещаемся ниже.
    y -= 18

    # Печатаем строку баланса.
    pdf.drawString(40, y, balance_text)

    # Смещаемся ниже перед блоком операций.
    y -= 35

    # Включаем жирный шрифт для заголовка блока операций.
    pdf.setFont("ArialCyrBold", 14)

    # Печатаем заголовок блока операций.
    pdf.drawString(40, y, "Операции")

    # Смещаемся ниже.
    y -= 22

    # Включаем жирный шрифт для шапки таблицы.
    pdf.setFont("ArialCyrBold", 10)

    # Печатаем заголовки колонок таблицы.
    pdf.drawString(40, y, "Дата")
    pdf.drawString(120, y, "Тип")
    pdf.drawString(210, y, "Категория")
    pdf.drawString(390, y, "Сумма")
    pdf.drawString(470, y, "Описание")

    # Смещаемся ниже после шапки таблицы.
    y -= 16

    # Включаем обычный шрифт для данных таблицы.
    pdf.setFont("ArialCyr", 9)

    # Проходим по каждой операции.
    for item in queryset:
        # Если нижнее поле страницы заканчивается, создаём новую страницу.
        if y < 60:
            # Завершаем текущую страницу.
            pdf.showPage()

            # Снова включаем обычный кириллический шрифт на новой странице.
            pdf.setFont("ArialCyr", 9)

            # Возвращаем курсор в верхнюю часть новой страницы.
            y = page_height - 50

        # Формируем текст даты операции.
        date_text = item.operation_date.strftime("%Y-%m-%d")

        # Формируем текст типа операции.
        type_text = item.get_transaction_type_display()

        # Формируем текст категории с полным именем.
        category_text = item.category.full_name if hasattr(item.category, "full_name") else item.category.name

        # Формируем текст суммы.
        amount_text = f"{item.amount:.2f}".replace(".", ",")

        # Формируем текст описания.
        description_text = item.description or "-"

        # Если категория слишком длинная, обрезаем её.
        if len(category_text) > 28:
            category_text = category_text[:25] + "..."

        # Если описание слишком длинное, обрезаем его.
        if len(description_text) > 22:
            description_text = description_text[:19] + "..."

        # Печатаем дату операции.
        pdf.drawString(40, y, date_text)

        # Печатаем тип операции.
        pdf.drawString(120, y, type_text)

        # Печатаем категорию операции.
        pdf.drawString(210, y, category_text)

        # Печатаем сумму операции.
        pdf.drawString(390, y, amount_text)

        # Печатаем описание операции.
        pdf.drawString(470, y, description_text)

        # Смещаемся на следующую строку таблицы.
        y -= 16

    # Завершаем генерацию PDF-файла.
    pdf.save()

    # Возвращаем готовый PDF-файл.
    return response