# Импортируем asyncio, чтобы запускать асинхронного Telegram-бота.
import asyncio
from pathlib import Path
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from django.conf import settings
from core.models import Transaction
from core.telegram_bot.keyboards import build_category_keyboard, build_main_menu
from core.telegram_bot.states import AddTransactionState
from core.services.ai_features import transcribe_audio_bytes
from core.services.telegram_helpers import (
    add_transaction_from_bot,
    add_transaction_from_voice_text,
    get_categories_for_user,
    get_category_report_text,
    get_compare_week_text,
    get_today_expenses_text,
    get_user_by_telegram_id,
    get_week_summary_text,
    link_telegram_account,
)

router = Router()


@router.message(F.text == "/start")
async def start_command(message: Message) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(
            "Здравствуйте!\n\n"
            "Вы на связи с <b>FinControl</b>.\n\n"
            "Чтобы начать работу, сначала привяжите Telegram к вашему аккаунту на сайте:\n"
            "1. Откройте веб-кабинет.\n"
            "2. Перейдите в раздел <b>Профиль</b>.\n"
            "3. Скопируйте персональный код привязки.\n"
            "4. Отправьте сюда команду:\n"
            "<code>/link ВАШ_КОД</code>"
        )
        return
    await message.answer(
        f"Здравствуйте, <b>{user.username}</b>!\n\n"
        "FinControl готов к работе.",
        reply_markup=build_main_menu(),
    )


@router.message(F.text == "/help")
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>Команды FinControl</b>\n\n"
        "/start — открыть главное меню\n"
        "/help — показать справку\n"
        "/today — сводка за сегодня\n"
        "/week — сводка за неделю\n"
        "/category Еда — расходы по категории\n"
        "/link ВАШ_КОД — привязать Telegram к аккаунту\n\n"
        "Если в профиле включён голосовой ввод, можно отправлять голосовые сообщения с операциями."
    )


@router.message(F.text.startswith("/link"))
async def link_command(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Пожалуйста, используйте команду так:\n<code>/link ВАШ_КОД</code>")
        return
    code = parts[1].strip().upper()
    success, response_text = await link_telegram_account(code=code, telegram_id=message.from_user.id)
    await message.answer(response_text)
    if success:
        await message.answer("Подключение завершено успешно.", reply_markup=build_main_menu())


@router.message(F.text == "/today")
async def today_command(message: Message) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        return
    response_text = await get_today_expenses_text(user)
    await message.answer(response_text)


@router.message(F.text == "/week")
async def week_command(message: Message) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        return
    response_text = await get_week_summary_text(user)
    await message.answer(response_text)


@router.message(F.text.startswith("/category"))
async def category_command(message: Message) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Пожалуйста, укажите категорию так:\n<code>/category Еда</code>")
        return
    response_text = await get_category_report_text(user, parts[1])
    await message.answer(response_text)


@router.callback_query(F.data == "menu_today")
async def menu_today(callback: CallbackQuery) -> None:
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        await callback.answer()
        return
    await callback.message.answer(await get_today_expenses_text(user))
    await callback.answer()


@router.callback_query(F.data == "menu_week")
async def menu_week(callback: CallbackQuery) -> None:
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        await callback.answer()
        return
    await callback.message.answer(await get_week_summary_text(user))
    await callback.answer()


@router.callback_query(F.data == "menu_compare")
async def menu_compare(callback: CallbackQuery) -> None:
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        await callback.answer()
        return
    await callback.message.answer(await get_compare_week_text(user))
    await callback.answer()


@router.callback_query(F.data == "menu_add_expense")
async def menu_add_expense(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        await callback.answer()
        return
    await state.update_data(transaction_type=Transaction.TYPE_EXPENSE)
    await state.set_state(AddTransactionState.amount)
    await callback.message.answer("Введите сумму расхода.\nПример: <code>1200.50</code>")
    await callback.answer()


@router.callback_query(F.data == "menu_add_income")
async def menu_add_income(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        await callback.answer()
        return
    await state.update_data(transaction_type=Transaction.TYPE_INCOME)
    await state.set_state(AddTransactionState.amount)
    await callback.message.answer("Введите сумму дохода.\nПример: <code>55000</code>")
    await callback.answer()


@router.message(AddTransactionState.amount)
async def process_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("Не удалось распознать сумму. Введите число, например <code>1500.50</code>.")
        return
    await state.update_data(amount=amount)
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        return
    categories = await get_categories_for_user(user)
    if not categories:
        await state.clear()
        await message.answer("У вас пока нет активных категорий. Сначала создайте их в веб-кабинете.")
        return
    await state.set_state(AddTransactionState.category_id)
    await message.answer("Выберите категорию операции:", reply_markup=build_category_keyboard(categories))


@router.callback_query(AddTransactionState.category_id, F.data.startswith("category_"))
async def process_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(AddTransactionState.description)
    await callback.message.answer("Введите описание операции или отправьте <code>-</code>.")
    await callback.answer()


@router.message(AddTransactionState.description)
async def process_description(message: Message, state: FSMContext) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        return
    data = await state.get_data()
    description = "" if (message.text or "").strip() == "-" else (message.text or "").strip()
    response_text = await add_transaction_from_bot(
        user=user,
        transaction_type=data["transaction_type"],
        amount=data["amount"],
        category_id=data["category_id"],
        description=description,
    )
    await state.clear()
    await message.answer(f"{response_text}\n\nОперация учтена.", reply_markup=build_main_menu())


@router.message(F.voice)
async def process_voice_message(message: Message) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала привяжите Telegram через команду:\n<code>/link ВАШ_КОД</code>")
        return
    await message.answer("Получила голосовое сообщение. Распознаю речь и пробую создать операцию...")
    file_info = await message.bot.get_file(message.voice.file_id)
    audio_stream = await message.bot.download_file(file_info.file_path)
    content = audio_stream.read()
    filename = Path(file_info.file_path).name or "voice.ogg"
    transcript = transcribe_audio_bytes(filename=filename, audio_bytes=content)
    if not transcript:
        await message.answer("Не удалось распознать голосовое сообщение. Можно продолжить обычным пошаговым добавлением.")
        return
    response_text = await add_transaction_from_voice_text(user=user, transcript=transcript)
    await message.answer(f"Распознанный текст:\n<code>{transcript}</code>\n\n{response_text}", reply_markup=build_main_menu())


async def start_bot() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в файле .env")
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


def run_bot() -> None:
    asyncio.run(start_bot())
