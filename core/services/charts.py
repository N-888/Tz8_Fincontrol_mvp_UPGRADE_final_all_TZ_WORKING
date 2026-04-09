# Импортируем base64, чтобы кодировать изображения графиков в строку.
import base64
from io import BytesIO
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def _format_money(value, _position=None) -> str:
    # Преобразуем число в денежную строку с двумя знаками после запятой.
    return f"{value:,.2f}".replace(",", " ")


def _short_date_labels(labels: list[str]) -> list[str]:
    # Создаём список для коротких подписей дат.
    result = []
    for label in labels:
        if isinstance(label, str) and len(label) >= 10 and label[4] == "-" and label[7] == "-":
            result.append(f"{label[8:10]}.{label[5:7]}")
        else:
            result.append(str(label))
    return result


def _prepare_pie_data(labels: list[str], values: list[float]) -> tuple[list[str], list[float]]:
    # Если категорий немного, возвращаем их без изменений.
    if len(labels) <= 6:
        return labels, values
    pairs = list(zip(labels, values))
    pairs.sort(key=lambda item: item[1], reverse=True)
    top_pairs = pairs[:5]
    other_sum = sum(value for _, value in pairs[5:])
    prepared_labels = [label for label, _ in top_pairs]
    prepared_values = [value for _, value in top_pairs]
    if other_sum > 0:
        prepared_labels.append("Другое")
        prepared_values.append(other_sum)
    return prepared_labels, prepared_values


def figure_to_base64() -> str:
    # Получаем текущую фигуру matplotlib.
    figure = plt.gcf()
    figure.tight_layout()
    buffer = BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", dpi=160, facecolor="white")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()
    plt.close(figure)
    return image_base64


def build_line_chart(labels: list[str], incomes: list[float], expenses: list[float]) -> str:
    # Если данных нет, строим компактную заглушку.
    if not labels:
        plt.figure(figsize=(8, 3.8))
        plt.text(0.5, 0.5, "Нет данных\nза выбранный период", ha="center", va="center", fontsize=14)
        plt.axis("off")
        return figure_to_base64()

    display_labels = _short_date_labels(labels)
    plt.figure(figsize=(8.2, 3.8))
    plt.plot(display_labels, incomes, marker="o", linewidth=2, label="Доходы")
    plt.plot(display_labels, expenses, marker="o", linewidth=2, label="Расходы")
    plt.title("Динамика доходов и расходов")
    plt.xlabel("Период")
    plt.ylabel("Сумма, ₽")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xticks(rotation=20, ha="right")
    plt.gca().yaxis.set_major_formatter(FuncFormatter(_format_money))
    plt.margins(x=0.02)
    return figure_to_base64()


def build_pie_chart(labels: list[str], values: list[float]) -> str:
    # Создаём новую фигуру диаграммы.
    plt.figure(figsize=(7.2, 4.8))
    if not values:
        plt.text(0.5, 0.5, "Нет расходов\nза выбранный период", ha="center", va="center", fontsize=14)
        plt.axis("off")
        return figure_to_base64()

    prepared_labels, prepared_values = _prepare_pie_data(labels, values)
    wrapped_labels = [textwrap.fill(label, width=14) for label in prepared_labels]
    wedges, _texts, _autotexts = plt.pie(
        prepared_values,
        labels=None,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.72,
    )
    plt.axis("equal")
    plt.title("Распределение расходов по категориям")
    plt.legend(
        wedges,
        wrapped_labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=9,
        frameon=False,
    )
    return figure_to_base64()
