# Импортируем состояния и группы состояний aiogram.
from aiogram.fsm.state import State, StatesGroup


class AddTransactionState(StatesGroup):
    # Создаём состояние выбора типа операции.
    transaction_type = State()

    # Создаём состояние ввода суммы.
    amount = State()

    # Создаём состояние выбора категории.
    category_id = State()

    # Создаём состояние ввода описания.
    description = State()
