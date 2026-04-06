# Импортируем InlineKeyboardBuilder, чтобы удобно и наглядно собирать встроенные кнопки Telegram.
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Создаём функцию для построения главного меню Telegram-бота.
def build_main_menu():
    # Создаём объект-конструктор встроенной клавиатуры.
    builder = InlineKeyboardBuilder()

    # Добавляем кнопку "Сегодня" с эмодзи точки-ориентира, чтобы день воспринимался как конкретная текущая точка.
    builder.button(text="📍 Сегодня", callback_data="menu_today")

    # Добавляем кнопку "Неделя" с календарным эмодзи, чтобы показать более широкий период.
    builder.button(text="📅 Неделя", callback_data="menu_week")

    # Добавляем кнопку "Сравнить" для сравнения текущих и предыдущих финансовых показателей.
    builder.button(text="📊 Сравнить", callback_data="menu_compare")

    # Добавляем кнопку "Добавить расход" с запрещающим знаком, чтобы визуально подчеркнуть уменьшение средств.
    builder.button(text="⛔ Добавить расход", callback_data="menu_add_expense")

    # Добавляем кнопку "Добавить доход" с денежным эмодзи, чтобы визуально подчеркнуть поступление средств.
    builder.button(text="💰 Добавить доход", callback_data="menu_add_income")

    # Располагаем кнопки по две в строке, а последнюю выводим отдельно для аккуратного и делового вида.
    builder.adjust(2, 2, 1)

    # Возвращаем готовую клавиатуру в формате, который понимает Telegram.
    return builder.as_markup()


# Создаём функцию для построения клавиатуры выбора категории.
def build_category_keyboard(categories):
    # Создаём объект-конструктор встроенной клавиатуры для списка категорий.
    builder = InlineKeyboardBuilder()

    # Проходим по всем категориям, которые были переданы в функцию.
    for category_id, category_title in categories:
        # Добавляем кнопку категории с названием и callback-данными, в которых хранится ID категории.
        builder.button(text=category_title, callback_data=f"category_{category_id}")

    # Располагаем кнопки категорий по одной в строке, чтобы их было проще читать и выбирать.
    builder.adjust(1)

    # Возвращаем готовую клавиатуру выбора категории в формате Telegram.
    return builder.as_markup()