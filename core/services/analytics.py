# Импортируем Decimal для точных денежных вычислений.
from decimal import Decimal
from datetime import timedelta
import pandas as pd
from django.db.models import Sum
from django.utils import timezone
from core.models import Advice, Anomaly, Transaction
from core.services.charts import build_line_chart, build_pie_chart
from core.services.ai_features import generate_ai_advice


def resolve_period(period: str, start_date=None, end_date=None):
    today = timezone.localdate()
    if period == "day":
        return today, today
    if period == "week":
        return today - timedelta(days=6), today
    if period == "month":
        return today.replace(day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    if period == "custom" and start_date and end_date:
        return start_date, end_date
    return None, None


def get_filtered_transactions(user, period="month", start_date=None, end_date=None, category_id=None):
    queryset = Transaction.objects.filter(user=user).select_related("category", "category__parent")
    period_start, period_end = resolve_period(period, start_date, end_date)
    if period_start:
        queryset = queryset.filter(operation_date__gte=period_start)
    if period_end:
        queryset = queryset.filter(operation_date__lte=period_end)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    return queryset


def queryset_to_dataframe(queryset) -> pd.DataFrame:
    raw_data = list(
        queryset.values(
            "id",
            "transaction_type",
            "amount",
            "operation_date",
            "category__name",
            "category__icon",
            "category__parent__name",
            "category__monthly_limit",
            "description",
        )
    )
    if not raw_data:
        return pd.DataFrame(
            columns=[
                "id",
                "transaction_type",
                "amount",
                "operation_date",
                "category__name",
                "category__icon",
                "category__parent__name",
                "category__monthly_limit",
                "description",
                "category_full_name",
            ]
        )
    dataframe = pd.DataFrame(raw_data)
    dataframe["operation_date"] = pd.to_datetime(dataframe["operation_date"])
    dataframe["amount"] = dataframe["amount"].astype(float)
    dataframe["category_full_name"] = dataframe.apply(
        lambda row: f"{row['category__parent__name']} → {row['category__name']}"
        if row.get("category__parent__name")
        else row["category__name"],
        axis=1,
    )
    return dataframe


def calculate_summary(queryset) -> dict:
    income_sum = queryset.filter(transaction_type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    expense_sum = queryset.filter(transaction_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    income_sum = income_sum.quantize(Decimal("0.01"))
    expense_sum = expense_sum.quantize(Decimal("0.01"))
    balance = (income_sum - expense_sum).quantize(Decimal("0.01"))
    return {
        "income_sum": income_sum,
        "expense_sum": expense_sum,
        "balance": balance,
    }


def build_timeseries(df: pd.DataFrame) -> tuple[list[str], list[float], list[float]]:
    if df.empty:
        return [], [], []
    working_df = df.copy()
    working_df["date_label"] = working_df["operation_date"].dt.strftime("%Y-%m-%d")
    income_group = (
        working_df[working_df["transaction_type"] == Transaction.TYPE_INCOME]
        .groupby("date_label")["amount"]
        .sum()
    )
    expense_group = (
        working_df[working_df["transaction_type"] == Transaction.TYPE_EXPENSE]
        .groupby("date_label")["amount"]
        .sum()
    )
    labels = sorted(set(income_group.index.tolist()) | set(expense_group.index.tolist()))
    incomes = [float(income_group.get(label, 0)) for label in labels]
    expenses = [float(expense_group.get(label, 0)) for label in labels]
    return labels, incomes, expenses


def build_category_distribution(df: pd.DataFrame) -> tuple[list[str], list[float]]:
    if df.empty:
        return [], []
    expenses_df = df[df["transaction_type"] == Transaction.TYPE_EXPENSE]
    if expenses_df.empty:
        return [], []
    grouped = expenses_df.groupby("category_full_name")["amount"].sum().sort_values(ascending=False)
    return grouped.index.tolist(), grouped.values.tolist()


def generate_advice(user, df: pd.DataFrame, summary: dict) -> list[str]:
    advice_list: list[str] = []
    if not user.profile.recommendations_enabled:
        return advice_list
    if summary["expense_sum"] > summary["income_sum"] and summary["income_sum"] > 0:
        advice_list.append("Расходы за период превысили доходы. Стоит сократить необязательные траты.")
    if user.profile.budget_limit and summary["expense_sum"] > user.profile.budget_limit:
        advice_list.append("Вы превысили общий бюджетный лимит. Проверьте самые крупные категории расходов.")
    if df.empty:
        return advice_list
    expenses_df = df[df["transaction_type"] == Transaction.TYPE_EXPENSE]
    if expenses_df.empty:
        advice_list.append("За выбранный период у вас нет расходов. Баланс выглядит отлично.")
        return advice_list
    category_totals = expenses_df.groupby("category_full_name")["amount"].sum().sort_values(ascending=False)
    top_category_name = category_totals.index[0]
    top_category_value = float(category_totals.iloc[0])
    total_expense = float(expenses_df["amount"].sum())
    if total_expense > 0 and (top_category_value / total_expense) >= 0.4:
        advice_list.append(f"Категория «{top_category_name}» занимает значительную часть расходов. Проверьте её подробнее.")
    for category in user.categories.filter(is_active=True).select_related("parent"):
        if not category.monthly_limit:
            continue
        category_spend = expenses_df.loc[expenses_df["category_full_name"] == category.full_name, "amount"].sum()
        if category_spend > float(category.monthly_limit):
            advice_list.append(f"Лимит по категории «{category.full_name}» превышен. Проверьте траты в этой группе.")
    if not advice_list:
        advice_list.append("Финансовая картина выглядит стабильно. Продолжайте фиксировать операции регулярно.")
    if user.profile.ai_advice_enabled:
        category_pairs = [(name, float(value)) for name, value in category_totals.items()]
        ai_tips = generate_ai_advice(summary=summary, advice_list=advice_list, category_totals=category_pairs)
        for tip in ai_tips:
            advice_list.append(f"AI: {tip}")
    return advice_list


def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    anomalies: list[dict] = []
    if df.empty:
        return anomalies
    expenses_df = df[df["transaction_type"] == Transaction.TYPE_EXPENSE].copy()
    if expenses_df.empty:
        return anomalies
    grouped = expenses_df.groupby([expenses_df["operation_date"].dt.date, "category_full_name"])["amount"].sum().reset_index()
    for category_name in grouped["category_full_name"].unique():
        category_data = grouped[grouped["category_full_name"] == category_name]
        if len(category_data) < 2:
            continue
        average_value = float(category_data["amount"].mean())
        max_row = category_data.loc[category_data["amount"].idxmax()]
        if average_value > 0 and float(max_row["amount"]) >= average_value * 1.8 and float(max_row["amount"]) - average_value >= 300:
            anomalies.append(
                {
                    "title": f"Резкий рост расходов по категории «{category_name}»",
                    "details": f"За {max_row['operation_date']} расходы составили {max_row['amount']:.2f}, что заметно выше среднего значения {average_value:.2f}.",
                    "category_name": category_name,
                }
            )
    return anomalies


def sync_insights(user, advice_list: list[str], anomalies: list[dict]) -> None:
    Advice.objects.filter(user=user).delete()
    Anomaly.objects.filter(user=user).delete()
    for index, advice_text in enumerate(advice_list, start=1):
        level = Advice.LEVEL_WARNING if "превыс" in advice_text.lower() or "сократ" in advice_text.lower() else Advice.LEVEL_INFO
        Advice.objects.create(user=user, level=level, text=advice_text, code=f"advice_{index}")
    for anomaly in anomalies:
        category = None
        for candidate in user.categories.select_related("parent").all():
            if candidate.full_name == anomaly["category_name"]:
                category = candidate
                break
        Anomaly.objects.create(user=user, title=anomaly["title"], details=anomaly["details"], category=category)


def build_dashboard_data(user, period="month", start_date=None, end_date=None, category_id=None) -> dict:
    queryset = get_filtered_transactions(
        user=user,
        period=period,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
    )
    df = queryset_to_dataframe(queryset)
    summary = calculate_summary(queryset)
    labels, incomes, expenses = build_timeseries(df)
    category_labels, category_values = build_category_distribution(df)
    advice_list = generate_advice(user, df, summary)
    anomaly_list = detect_anomalies(df)
    sync_insights(user, advice_list, anomaly_list)
    line_chart = build_line_chart(labels, incomes, expenses)
    pie_chart = build_pie_chart(category_labels, category_values)
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
    data = build_dashboard_data(user=user, period=period)
    income_sum = data["summary"]["income_sum"]
    expense_sum = data["summary"]["expense_sum"]
    balance = data["summary"]["balance"]
    period_title_map = {
        "day": "за сегодня",
        "week": "за неделю",
        "month": "за месяц",
        "year": "за год",
    }
    period_title = period_title_map.get(period, "за период")
    first_advice = data["advice_list"][0] if data["advice_list"] else "Рекомендаций пока нет."
    return (
        f"📊 Сводка {period_title}\n"
        f"• Доходы: {income_sum:.2f}\n"
        f"• Расходы: {expense_sum:.2f}\n"
        f"• Баланс: {balance:.2f}\n\n"
        f"💡 Совет: {first_advice}"
    )
