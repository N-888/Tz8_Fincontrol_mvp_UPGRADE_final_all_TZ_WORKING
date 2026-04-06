# Импортируем base64, чтобы кодировать изображения графиков в строку.
import base64

# Импортируем BytesIO, чтобы хранить изображение в памяти.
from io import BytesIO

# Импортируем matplotlib и явно переводим его в безэкранный режим для серверной генерации.
import matplotlib

# Устанавливаем серверный backend, чтобы графики строились без GUI.
matplotlib.use("Agg")

# Импортируем pyplot для построения графиков.
import matplotlib.pyplot as plt


def figure_to_base64() -> str:
    # Создаём буфер в памяти для сохранения изображения.
    buffer = BytesIO()

    # Сохраняем текущую фигуру в PNG-формате.
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=140)

    # Перемещаем указатель в начало буфера.
    buffer.seek(0)

    # Кодируем байты изображения в base64-строку.
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    # Закрываем буфер, чтобы освободить память.
    buffer.close()

    # Закрываем текущую фигуру matplotlib.
    plt.close()

    # Возвращаем готовую строку.
    return image_base64


def build_line_chart(labels: list[str], incomes: list[float], expenses: list[float]) -> str:
    # Создаём новую фигуру графика.
    plt.figure(figsize=(10, 4.5))

    # Строим линию доходов.
    plt.plot(labels, incomes, marker="o", linewidth=2, label="Доходы")

    # Строим линию расходов.
    plt.plot(labels, expenses, marker="o", linewidth=2, label="Расходы")

    # Добавляем заголовок графика.
    plt.title("Динамика доходов и расходов")

    # Подписываем ось X.
    plt.xlabel("Период")

    # Подписываем ось Y.
    plt.ylabel("Сумма")

    # Включаем сетку для лучшей читаемости.
    plt.grid(True, alpha=0.3)

    # Добавляем легенду.
    plt.legend()

    # Поворачиваем подписи, чтобы они не налезали друг на друга.
    plt.xticks(rotation=25, ha="right")

    # Возвращаем график в виде строки base64.
    return figure_to_base64()


def build_pie_chart(labels: list[str], values: list[float]) -> str:
    # Создаём новую фигуру диаграммы.
    plt.figure(figsize=(6, 6))

    # Если данных нет, строим заглушку.
    if not values:
        # Выводим текст по центру пустой диаграммы.
        plt.text(0.5, 0.5, "Нет расходов\nза выбранный период", ha="center", va="center", fontsize=14)

        # Отключаем оси, чтобы вид был чище.
        plt.axis("off")

        # Возвращаем картинку-заглушку.
        return figure_to_base64()

    # Строим круговую диаграмму.
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)

    # Делаем диаграмму идеально круглой.
    plt.axis("equal")

    # Добавляем заголовок.
    plt.title("Распределение расходов по категориям")

    # Возвращаем диаграмму в виде строки base64.
    return figure_to_base64()
