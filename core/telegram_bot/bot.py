# Импортируем asyncio, чтобы запускать асинхронного Telegram-бота.
import asyncio

# Импортируем основные классы aiogram для создания бота, диспетчера, роутера и фильтров.
from aiogram import Bot, Dispatcher, F, Router

# Импортируем типы callback-запросов и обычных сообщений Telegram.
from aiogram.types import CallbackQuery, Message

# Импортируем контекст FSM, чтобы хранить промежуточные шаги сценария добавления операции.
from aiogram.fsm.context import FSMContext

# Импортируем простое хранилище FSM в памяти для текущего MVP-проекта.
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем стандартные свойства бота для установки режима форматирования сообщений.
from aiogram.client.default import DefaultBotProperties

# Импортируем режим HTML, чтобы красиво выделять текст в сообщениях Telegram.
from aiogram.enums import ParseMode

# Импортируем настройки Django-проекта, чтобы взять токен Telegram-бота из settings.
from django.conf import settings

# Импортируем модель Transaction, чтобы использовать константы типов дохода и расхода.
from core.models import Transaction

# Импортируем функции построения клавиатур Telegram-бота.
from core.telegram_bot.keyboards import build_category_keyboard, build_main_menu

# Импортируем состояния FSM для пошагового добавления операции.
from core.telegram_bot.states import AddTransactionState

# Импортируем сервисные функции, через которые бот работает с пользователем и данными.
from core.services.telegram_helpers import (
    add_transaction_from_bot,
    get_categories_for_user,
    get_category_report_text,
    get_compare_week_text,
    get_today_expenses_text,
    get_user_by_telegram_id,
    get_week_summary_text,
    link_telegram_account,
)

# Создаём роутер, в котором будут зарегистрированы все обработчики команд и кнопок бота.
router = Router()


# Регистрируем обработчик команды /start.
@router.message(F.text == "/start")
async def start_command(message: Message) -> None:
    # Получаем пользователя сайта по Telegram ID отправителя.
    user = await get_user_by_telegram_id(message.from_user.id)

    # Проверяем, привязан ли уже Telegram к аккаунту сайта.
    if not user:
        # Если привязки ещё нет, отправляем спокойную и понятную инструкцию по подключению.
        await message.answer(
            "Здравствуйте!\n\n"
            "Вы на связи с <b>FinControl</b> — сервисом для уверенного и осознанного управления личными финансами.\n\n"
            "Чтобы начать работу, сначала привяжите Telegram к вашему аккаунту на сайте:\n"
            "1. Откройте веб-кабинет.\n"
            "2. Перейдите в раздел <b>Профиль</b>.\n"
            "3. Скопируйте персональный код привязки.\n"
            "4. Отправьте сюда команду:\n"
            "<code>/link ВАШ_КОД</code>\n\n"
            "После привязки бот поможет вам быстрее фиксировать операции, следить за динамикой расходов и принимать более сильные финансовые решения.",
        )

        # Завершаем обработчик, потому что показывать меню до привязки нельзя.
        return

    # Если пользователь уже привязан, отправляем приветствие и показываем главное меню.
    await message.answer(
        f"Здравствуйте, <b>{user.username}</b>!\n\n"
        "FinControl готов к работе.\n"
        "Выберите действие ниже — и я помогу вам держать финансы под контролем спокойно, понятно и системно.",
        reply_markup=build_main_menu(),
    )


# Регистрируем обработчик команды /help.
@router.message(F.text == "/help")
async def help_command(message: Message) -> None:
    # Отправляем пользователю краткую, но содержательную справку по основным командам.
    await message.answer(
        "<b>Команды FinControl</b>\n\n"
        "/start — открыть главное меню\n"
        "/help — показать справку\n"
        "/today — сводка за сегодня\n"
        "/week — сводка за неделю\n"
        "/category Еда — расходы по категории\n"
        "/link ВАШ_КОД — привязать Telegram к аккаунту\n\n"
        "Рекомендация:\n"
        "Фиксируйте доходы и расходы регулярно — даже небольшая финансовая дисциплина со временем заметно усиливает устойчивость, помогает лучше управлять целями и даёт больше свободы в принятии решений.",
    )


# Регистрируем обработчик команды /link.
@router.message(F.text.startswith("/link"))
async def link_command(message: Message) -> None:
    # Разбиваем текст сообщения на части по пробелам.
    parts = (message.text or "").split()

    # Проверяем, передал ли пользователь код после команды /link.
    if len(parts) < 2:
        # Если код не передан, показываем правильный формат команды.
        await message.answer(
            "Пожалуйста, используйте команду в таком формате:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Завершаем обработчик.
        return

    # Берём вторую часть сообщения как код привязки и переводим его в верхний регистр.
    code = parts[1].strip().upper()

    # Пытаемся привязать Telegram-аккаунт к профилю пользователя сайта.
    success, response_text = await link_telegram_account(
        code=code,
        telegram_id=message.from_user.id,
    )

    # Отправляем результат привязки в чат.
    await message.answer(response_text)

    # Проверяем, успешно ли завершилась привязка.
    if success:
        # После успешной привязки отправляем подтверждение и главное меню.
        await message.answer(
            "Подключение завершено успешно.\n\n"
            "Теперь вы можете быстро получать сводки, добавлять операции и поддерживать порядок в личных финансах прямо из Telegram.",
            reply_markup=build_main_menu(),
        )


# Регистрируем обработчик команды /today.
@router.message(F.text == "/today")
async def today_command(message: Message) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(message.from_user.id)

    # Проверяем, привязан ли Telegram к аккаунту сайта.
    if not user:
        # Если привязки нет, просим сначала выполнить подключение.
        await message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Завершаем обработчик.
        return

    # Получаем готовую дневную сводку через сервисную функцию.
    response_text = await get_today_expenses_text(user)

    # Отправляем пользователю сводку за сегодняшний день.
    await message.answer(response_text)


# Регистрируем обработчик команды /week.
@router.message(F.text == "/week")
async def week_command(message: Message) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(message.from_user.id)

    # Проверяем, привязан ли Telegram к аккаунту сайта.
    if not user:
        # Если привязки нет, просим сначала выполнить подключение.
        await message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Завершаем обработчик.
        return

    # Получаем готовую недельную сводку через сервисную функцию.
    response_text = await get_week_summary_text(user)

    # Отправляем пользователю сводку за неделю.
    await message.answer(response_text)


# Регистрируем обработчик команды /category.
@router.message(F.text.startswith("/category"))
async def category_command(message: Message) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(message.from_user.id)

    # Проверяем, привязан ли Telegram к аккаунту сайта.
    if not user:
        # Если привязки нет, просим сначала выполнить подключение.
        await message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Завершаем обработчик.
        return

    # Разделяем текст сообщения на команду и название категории.
    parts = (message.text or "").split(maxsplit=1)

    # Проверяем, передал ли пользователь название категории.
    if len(parts) < 2:
        # Если название не передано, показываем правильный формат запроса.
        await message.answer(
            "Пожалуйста, укажите категорию в таком формате:\n"
            "<code>/category Еда</code>"
        )

        # Завершаем обработчик.
        return

    # Получаем текст отчёта по указанной категории.
    response_text = await get_category_report_text(user, parts[1])

    # Отправляем сформированный отчёт в чат.
    await message.answer(response_text)


# Регистрируем обработчик нажатия кнопки "Сегодня".
@router.callback_query(F.data == "menu_today")
async def menu_today(callback: CallbackQuery) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(callback.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, просим сначала выполнить подключение.
        await callback.message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Закрываем индикатор нажатия кнопки.
        await callback.answer()

        # Завершаем обработчик.
        return

    # Получаем текст дневной сводки.
    response_text = await get_today_expenses_text(user)

    # Отправляем сводку в чат.
    await callback.message.answer(response_text)

    # Закрываем индикатор нажатия кнопки.
    await callback.answer()


# Регистрируем обработчик нажатия кнопки "Неделя".
@router.callback_query(F.data == "menu_week")
async def menu_week(callback: CallbackQuery) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(callback.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, просим сначала выполнить подключение.
        await callback.message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Закрываем индикатор нажатия кнопки.
        await callback.answer()

        # Завершаем обработчик.
        return

    # Получаем недельную сводку через сервисную функцию.
    response_text = await get_week_summary_text(user)

    # Отправляем недельную сводку в чат.
    await callback.message.answer(response_text)

    # Закрываем индикатор нажатия кнопки.
    await callback.answer()


# Регистрируем обработчик нажатия кнопки "Сравнить".
@router.callback_query(F.data == "menu_compare")
async def menu_compare(callback: CallbackQuery) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(callback.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, просим сначала выполнить подключение.
        await callback.message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Закрываем индикатор нажатия кнопки.
        await callback.answer()

        # Завершаем обработчик.
        return

    # Получаем готовый текст сравнения текущей и прошлой недели.
    response_text = await get_compare_week_text(user)

    # Отправляем результат сравнения в чат.
    await callback.message.answer(response_text)

    # Закрываем индикатор нажатия кнопки.
    await callback.answer()


# Регистрируем обработчик нажатия кнопки "Добавить расход".
@router.callback_query(F.data == "menu_add_expense")
async def menu_add_expense(callback: CallbackQuery, state: FSMContext) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(callback.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, просим сначала выполнить подключение.
        await callback.message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Закрываем индикатор нажатия кнопки.
        await callback.answer()

        # Завершаем обработчик.
        return

    # Сохраняем в FSM тип операции как расход.
    await state.update_data(transaction_type=Transaction.TYPE_EXPENSE)

    # Переводим FSM на шаг ввода суммы.
    await state.set_state(AddTransactionState.amount)

    # Просим пользователя ввести сумму расхода.
    await callback.message.answer(
        "Введите сумму расхода.\n"
        "Пример: <code>1200.50</code>\n\n"
        "Чем аккуратнее вы фиксируете траты, тем точнее становятся ваша аналитика и финансовые решения."
    )

    # Закрываем индикатор нажатия кнопки.
    await callback.answer()


# Регистрируем обработчик нажатия кнопки "Добавить доход".
@router.callback_query(F.data == "menu_add_income")
async def menu_add_income(callback: CallbackQuery, state: FSMContext) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(callback.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, просим сначала выполнить подключение.
        await callback.message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Закрываем индикатор нажатия кнопки.
        await callback.answer()

        # Завершаем обработчик.
        return

    # Сохраняем в FSM тип операции как доход.
    await state.update_data(transaction_type=Transaction.TYPE_INCOME)

    # Переводим FSM на шаг ввода суммы.
    await state.set_state(AddTransactionState.amount)

    # Просим пользователя ввести сумму дохода.
    await callback.message.answer(
        "Введите сумму дохода.\n"
        "Пример: <code>55000</code>\n\n"
        "Регулярная фиксация доходов помогает видеть реальную финансовую картину и увереннее планировать следующие шаги."
    )

    # Закрываем индикатор нажатия кнопки.
    await callback.answer()


# Регистрируем обработчик шага FSM, на котором пользователь вводит сумму операции.
@router.message(AddTransactionState.amount)
async def process_amount(message: Message, state: FSMContext) -> None:
    # Пытаемся преобразовать введённый текст в число с плавающей точкой.
    try:
        # Заменяем запятую на точку, чтобы пользователь мог вводить сумму в привычном формате.
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        # Если преобразование не удалось, просим пользователя ввести сумму ещё раз.
        await message.answer(
            "Не удалось распознать сумму.\n"
            "Пожалуйста, введите число в таком формате:\n"
            "<code>1500</code>\n"
            "или\n"
            "<code>1500.50</code>"
        )

        # Завершаем обработчик, не переходя к следующему шагу.
        return

    # Сохраняем распознанную сумму в памяти FSM.
    await state.update_data(amount=amount)

    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(message.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, очищаем состояние.
        await state.clear()

        # Просим сначала привязать аккаунт.
        await message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Завершаем обработчик.
        return

    # Получаем список активных категорий пользователя.
    categories = await get_categories_for_user(user)

    # Проверяем, есть ли у пользователя активные категории.
    if not categories:
        # Если категорий нет, очищаем состояние.
        await state.clear()

        # Сообщаем, что сначала нужно создать категории в веб-кабинете.
        await message.answer(
            "У вас пока нет активных категорий.\n"
            "Сначала создайте их в веб-кабинете, чтобы операции учитывались корректно и аналитика была действительно полезной."
        )

        # Завершаем обработчик.
        return

    # Переводим FSM на следующий шаг выбора категории.
    await state.set_state(AddTransactionState.category_id)

    # Отправляем пользователю клавиатуру с категориями.
    await message.answer(
        "Выберите категорию операции:",
        reply_markup=build_category_keyboard(categories),
    )


# Регистрируем обработчик нажатия кнопки выбора категории во время FSM-сценария.
@router.callback_query(AddTransactionState.category_id, F.data.startswith("category_"))
async def process_category(callback: CallbackQuery, state: FSMContext) -> None:
    # Извлекаем ID категории из строки callback_data.
    category_id = int(callback.data.split("_")[1])

    # Сохраняем выбранный ID категории в FSM.
    await state.update_data(category_id=category_id)

    # Переводим FSM на шаг ввода описания операции.
    await state.set_state(AddTransactionState.description)

    # Просим пользователя ввести описание операции или дефис, если описание не требуется.
    await callback.message.answer(
        "Введите описание операции.\n"
        "Если описание не нужно, отправьте символ:\n"
        "<code>-</code>"
    )

    # Закрываем индикатор нажатия кнопки.
    await callback.answer()


# Регистрируем обработчик шага FSM, на котором пользователь вводит описание операции.
@router.message(AddTransactionState.description)
async def process_description(message: Message, state: FSMContext) -> None:
    # Получаем пользователя сайта по Telegram ID.
    user = await get_user_by_telegram_id(message.from_user.id)

    # Проверяем, найден ли пользователь.
    if not user:
        # Если пользователь не найден, очищаем состояние.
        await state.clear()

        # Просим сначала привязать аккаунт.
        await message.answer(
            "Сначала привяжите Telegram к вашему аккаунту через команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )

        # Завершаем обработчик.
        return

    # Получаем все ранее накопленные данные из FSM.
    data = await state.get_data()

    # Проверяем, ввёл ли пользователь дефис вместо описания.
    if (message.text or "").strip() == "-":
        # Если введён дефис, сохраняем пустое описание.
        description = ""
    else:
        # Иначе сохраняем введённый текст как описание операции.
        description = (message.text or "").strip()

    # Передаём данные в сервис создания операции из Telegram-бота.
    response_text = await add_transaction_from_bot(
        user=user,
        transaction_type=data["transaction_type"],
        amount=data["amount"],
        category_id=data["category_id"],
        description=description,
    )

    # После успешного завершения сценария очищаем FSM.
    await state.clear()

    # Отправляем результат пользователю и снова показываем главное меню.
    await message.answer(
        f"{response_text}\n\n"
        "Операция учтена.\n"
        "Последовательный учёт даже небольших сумм помогает выстраивать более устойчивую и сильную финансовую систему вокруг ваших целей.",
        reply_markup=build_main_menu(),
    )


# Создаём асинхронную функцию полноценного запуска бота.
async def start_bot() -> None:
    # Проверяем, задан ли токен Telegram-бота в настройках проекта.
    if not settings.TELEGRAM_BOT_TOKEN:
        # Если токен не найден, поднимаем понятную ошибку.
        raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в файле .env")

    # Создаём экземпляр Telegram-бота с HTML-форматированием сообщений.
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Создаём диспетчер aiogram с хранением FSM-состояний в памяти.
    dispatcher = Dispatcher(storage=MemoryStorage())

    # Подключаем роутер с обработчиками к диспетчеру.
    dispatcher.include_router(router)

    # Запускаем long polling для получения обновлений от Telegram.
    await dispatcher.start_polling(bot)


# Создаём обычную синхронную функцию-обёртку для запуска бота из Django management-команды.
def run_bot() -> None:
    # Запускаем асинхронную функцию старта через asyncio.
    asyncio.run(start_bot())