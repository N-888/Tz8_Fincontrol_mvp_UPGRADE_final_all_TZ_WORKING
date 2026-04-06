# Импортируем Decimal для точных денежных вычислений.
from decimal import Decimal

# Импортируем timedelta для расчёта периодов.
from datetime import timedelta

# Импортируем pandas для аналитики данных.
import pandas as pd

# Импортируем функции агрегации Django ORM.
from django.db.models import Sum

# Импортируем timezone для работы с датами.
from django.utils import timezone

# Импортируем локальные модели.
from core.models import Advice, Anomaly, Transaction

# Импортируем функции построения графиков.
from core.services.charts import build_line_chart, build_pie_chart


def resolve_period(period: str, start_date=None, end_date=None):
    # Получаем сегодняшнюю локальную дату.
    today = timezone.localdate()

    # Обрабатываем фильтр "день".
    if period == "day":
        return today, today

    # Обрабатываем фильтр "неделя".
    if period == "week":
        return today - timedelta(days=6), today

    # Обрабатываем фильтр "месяц".
    if period == "month":
        return today.replace(day=1), today

    # Обрабатываем фильтр "год".
    if period == "year":
        return today.replace(month=1, day=1), today

    # Обрабатываем произвольный период.
    if period == "custom" and start_date and end_date:
        return start_date, end_date

    # Возвращаем период "всё время", если фильтр не распознан.
    return None, None


def get_filtered_transactions(user, period="month", start_date=None, end_date=None, category_id=None):
    # Получаем начальную и конечную дату периода.
    period_start, period_end = resolve_period(period, start_date, end_date)

    # Берём только операции текущего пользователя.
    queryset = Transaction.objects.filter(user=user).select_related("category")

    # Если начало периода указано, фильтруем снизу.
    if period_start:
        queryset = queryset.filter(operation_date__gte=period_start)

    # Если конец периода указан, фильтруем сверху.
    if period_end:
        queryset = queryset.filter(operation_date__lte=period_end)

    # Если категория указана, фильтруем по категории.
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # Возвращаем готовый queryset.
    return queryset


def queryset_to_dataframe(queryset) -> pd.DataFrame:
    # Превращаем queryset в список словарей.
    raw_data = list(
        queryset.values(
            "id",
            "transaction_type",
            "amount",
            "operation_date",
            "category__name",
            "category__monthly_limit",
            "description",
        )
    )

    # Если данных нет, возвращаем пустой DataFrame с ожидаемыми колонками.
    if not raw_data:
        return pd.DataFrame(
            columns=[
                "id",
                "transaction_type",
                "amount",
                "operation_date",
                "category__name",
                "category__monthly_limit",
                "description",
            ]
        )

    # Создаём DataFrame из списка операций.
    dataframe = pd.DataFrame(raw_data)

    # Переводим даты в формат pandas datetime.
    dataframe["operation_date"] = pd.to_datetime(dataframe["operation_date"])

    # Переводим суммы в float для удобной группировки и построения графиков.
    dataframe["amount"] = dataframe["amount"].astype(float)

    # Возвращаем подготовленный DataFrame.
    return dataframe


def calculate_summary(queryset) -> dict:
    # Считаем общую сумму доходов.
    income_sum = queryset.filter(transaction_type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Считаем общую сумму расходов.
    expense_sum = queryset.filter(transaction_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Вычисляем баланс как разницу доходов и расходов.
    balance = income_sum - expense_sum

    # Возвращаем словарь итогов.
    return {
        "income_sum": income_sum,
        "expense_sum": expense_sum,
        "balance": balance,
    }


def build_timeseries(df: pd.DataFrame) -> tuple[list[str], list[float], list[float]]:
    # Если таблица пустая, возвращаем пустые данные.
    if df.empty:
        return [], [], []

    # Копируем таблицу, чтобы не менять исходные данные.
    working_df = df.copy()

    # Выделяем колонку даты без времени.
    working_df["date_label"] = working_df["operation_date"].dt.strftime("%Y-%m-%d")

    # Собираем сумму доходов по дням.
    income_group = (
        working_df[working_df["transaction_type"] == Transaction.TYPE_INCOME]
        .groupby("date_label")["amount"]
        .sum()
    )

    # Собираем сумму расходов по дням.
    expense_group = (
        working_df[working_df["transaction_type"] == Transaction.TYPE_EXPENSE]
        .groupby("date_label")["amount"]
        .sum()
    )

    # Собираем полный отсортированный список дат.
    labels = sorted(set(income_group.index.tolist()) | set(expense_group.index.tolist()))

    # Формируем значения доходов по всем датам.
    incomes = [float(income_group.get(label, 0)) for label in labels]

    # Формируем значения расходов по всем датам.
    expenses = [float(expense_group.get(label, 0)) for label in labels]

    # Возвращаем наборы данных для линейного графика.
    return labels, incomes, expenses


def build_category_distribution(df: pd.DataFrame) -> tuple[list[str], list[float]]:
    # Если таблица пустая, возвращаем пустые данные.
    if df.empty:
        return [], []

    # Оставляем только расходы.
    expenses_df = df[df["transaction_type"] == Transaction.TYPE_EXPENSE]

    # Если расходов нет, возвращаем пустые данные.
    if expenses_df.empty:
        return [], []

    # Группируем расходы по названию категории.
    grouped = expenses_df.groupby("category__name")["amount"].sum().sort_values(ascending=False)

    # Возвращаем подписи и значения диаграммы.
    return grouped.index.tolist(), grouped.values.tolist()


def generate_advice(user, df: pd.DataFrame, summary: dict) -> list[str]:
    # Создаём пустой список рекомендаций.
    advice_list: list[str] = []

    # Если рекомендации отключены, возвращаем пустой список.
    if not user.profile.recommendations_enabled:
        return advice_list

    # Если расходов больше доходов, добавляем предупреждение.
    if summary["expense_sum"] > summary["income_sum"] and summary["income_sum"] > 0:
        advice_list.append("Расходы за период превысили доходы. Стоит сократить необязательные траты.")

    # Если общий лимит задан и превышен, добавляем предупреждение.
    if user.profile.budget_limit and summary["expense_sum"] > user.profile.budget_limit:
        advice_list.append("Вы превысили общий бюджетный лимит. Проверьте самые крупные категории расходов.")

    # Если данных нет, возвращаем то, что уже накопили.
    if df.empty:
        return advice_list

    # Оставляем только расходы.
    expenses_df = df[df["transaction_type"] == Transaction.TYPE_EXPENSE]

    # Если расходов нет, даём позитивный совет.
    if expenses_df.empty:
        advice_list.append("За выбранный период у вас нет расходов. Баланс выглядит отлично.")
        return advice_list

    # Находим расходы по категориям.
    category_totals = expenses_df.groupby("category__name")["amount"].sum().sort_values(ascending=False)

    # Берём самую крупную категорию.
    top_category_name = category_totals.index[0]

    # Берём сумму самой крупной категории.
    top_category_value = float(category_totals.iloc[0])

    # Считаем общую сумму расходов.
    total_expense = float(expenses_df["amount"].sum())

    # Если доля самой крупной категории заметная, добавляем совет.
    if total_expense > 0 and (top_category_value / total_expense) >= 0.4:
        advice_list.append(f"Категория «{top_category_name}» занимает значительную часть расходов. Проверьте её подробнее.")

    # Проходим по категориям пользователя.
    for category in user.categories.filter(is_active=True):
        # Пропускаем категории без лимита.
        if not category.monthly_limit:
            continue

        # Считаем расходы по текущей категории в выборке.
        category_spend = expenses_df.loc[expenses_df["category__name"] == category.name, "amount"].sum()

        # Если лимит превышен, добавляем предупреждение.
        if category_spend > float(category.monthly_limit):
            advice_list.append(f"Лимит по категории «{category.name}» превышен. Проверьте траты в этой группе.")

    # Если рекомендаций не набралось, добавляем нейтральный совет.
    if not advice_list:
        advice_list.append("Финансовая картина выглядит стабильно. Продолжайте фиксировать операции регулярно.")

    # Возвращаем список советов.
    return advice_list


def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    # Создаём пустой список аномалий.
    anomalies: list[dict] = []

    # Если данных мало или нет, возвращаем пустой список.
    if df.empty:
        return anomalies

    # Оставляем только расходы.
    expenses_df = df[df["transaction_type"] == Transaction.TYPE_EXPENSE].copy()

    # Если расходов нет, возвращаем пустой список.
    if expenses_df.empty:
        return anomalies

    # Группируем расходы по датам и категориям.
    grouped = expenses_df.groupby([expenses_df["operation_date"].dt.date, "category__name"])["amount"].sum().reset_index()

    # Проходим по всем уникальным категориям.
    for category_name in grouped["category__name"].unique():
        # Берём данные только по одной категории.
        category_data = grouped[grouped["category__name"] == category_name]

        # Пропускаем категорию, если записей слишком мало.
        if len(category_data) < 2:
            continue

        # Считаем среднее значение расходов по категории.
        average_value = float(category_data["amount"].mean())

        # Находим максимальное значение.
        max_row = category_data.loc[category_data["amount"].idxmax()]

        # Если пик существенно выше среднего, считаем это аномалией.
        if average_value > 0 and float(max_row["amount"]) >= average_value * 1.8 and float(max_row["amount"]) - average_value >= 300:
            anomalies.append(
                {
                    "title": f"Резкий рост расходов по категории «{category_name}»",
                    "details": f"За {max_row['operation_date']} расходы составили {max_row['amount']:.2f}, что заметно выше среднего значения {average_value:.2f}.",
                    "category_name": category_name,
                }
            )

    # Возвращаем список найденных аномалий.
    return anomalies


def sync_insights(user, advice_list: list[str], anomalies: list[dict]) -> None:
    # Удаляем старые советы пользователя, чтобы хранить только актуальные.
    Advice.objects.filter(user=user).delete()

    # Удаляем старые аномалии пользователя.
    Anomaly.objects.filter(user=user).delete()

    # Проходим по рекомендациям.
    for index, advice_text in enumerate(advice_list, start=1):
        # Определяем уровень совета по тексту.
        level = Advice.LEVEL_WARNING if "превыс" in advice_text.lower() or "сократ" in advice_text.lower() else Advice.LEVEL_INFO

        # Создаём новую запись совета.
        Advice.objects.create(user=user, level=level, text=advice_text, code=f"advice_{index}")

    # Проходим по найденным аномалиям.
    for anomaly in anomalies:
        # Ищем связанную категорию по названию.
        category = user.categories.filter(name=anomaly["category_name"]).first()

        # Создаём запись аномалии.
        Anomaly.objects.create(user=user, title=anomaly["title"], details=anomaly["details"], category=category)


def build_dashboard_data(user, period="month", start_date=None, end_date=None, category_id=None) -> dict:
    # Получаем отфильтрованный набор операций.
    queryset = get_filtered_transactions(
        user=user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )

    # Превращаем операции в DataFrame.
    df = queryset_to_dataframe(queryset)

    # Считаем основные итоговые показатели.
    summary = calculate_summary(queryset)

    # Собираем данные для линейного графика.
    labels, incomes, expenses = build_timeseries(df)

    # Собираем данные для круговой диаграммы.
    category_labels, category_values = build_category_distribution(df)

    # Генерируем рекомендации.
    advice_list = generate_advice(user, df, summary)

    # Ищем аномалии.
    anomaly_list = detect_anomalies(df)

    # Синхронизируем советы и аномалии с базой данных.
    sync_insights(user, advice_list, anomaly_list)

    # Строим линейный график.
    line_chart = build_line_chart(labels, incomes, expenses)

    # Строим круговую диаграмму.
    pie_chart = build_pie_chart(category_labels, category_values)

    # Возвращаем полный словарь данных для интерфейса.
    return {
        "queryset": queryset,
        "summary": summary,
        "line_chart": line_chart,
        "pie_chart": pie_chart,
        "advice_list": advice_list,
        "anomaly_list": anomaly_list,
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "selected_category_id": category_id,
    }


def build_text_summary_for_period(user, period="day") -> str:
    # Получаем аналитику по выбранному периоду.
    data = build_dashboard_data(user=user, period=period)

    # Извлекаем итоговые значения.
    income_sum = data["summary"]["income_sum"]
    expense_sum = data["summary"]["expense_sum"]
    balance = data["summary"]["balance"]

    # Определяем красивое название периода.
    period_title_map = {
        "day": "за сегодня",
        "week": "за неделю",
        "month": "за месяц",
        "year": "за год",
    }

    # Получаем подпись периода.
    period_title = period_title_map.get(period, "за период")

    # Берём первую рекомендацию, если она есть.
    first_advice = data["advice_list"][0] if data["advice_list"] else "Рекомендаций пока нет."

    # Формируем текстовую сводку.
    return (
        f"📊 Сводка {period_title}\n"
        f"• Доходы: {income_sum:.2f}\n"
        f"• Расходы: {expense_sum:.2f}\n"
        f"• Баланс: {balance:.2f}\n\n"
        f"💡 Совет: {first_advice}"
    )
