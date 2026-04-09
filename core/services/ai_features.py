# Импортируем os, чтобы читать ключ API и названия моделей из переменных окружения.
import os
import re
from decimal import Decimal
from datetime import datetime
from typing import Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def is_openai_available() -> bool:
    # Если клиент SDK не импортировался, сразу возвращаем False.
    if OpenAI is None:
        return False
    return bool(os.getenv("OPENAI_API_KEY"))


def _get_client():
    # Если SDK или ключ не готовы, возвращаем None.
    if not is_openai_available():
        return None
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_ai_advice(summary: dict, advice_list: list[str], category_totals: list[tuple[str, float]]) -> list[str]:
    # Если внешний AI недоступен, возвращаем пустой список.
    if not is_openai_available():
        return []
    client = _get_client()
    if client is None:
        return []
    categories_text = "\n".join([f"- {name}: {value:.2f}" for name, value in category_totals[:10]]) or "Нет данных по категориям."
    free_advice_text = "\n".join([f"- {item}" for item in advice_list]) or "Бесплатные советы пока не сформированы."
    prompt = (
        "Ты помощник сервиса личных финансов. "
        "Сформируй 2 короткие практичные рекомендации на русском языке. "
        "Не повторяй уже имеющиеся советы дословно. "
        "Не используй нумерацию длиннее двух пунктов. "
        "Советы должны быть деловыми, спокойными и понятными обычному пользователю.\n\n"
        f"Доходы: {summary['income_sum']:.2f}\n"
        f"Расходы: {summary['expense_sum']:.2f}\n"
        f"Баланс: {summary['balance']:.2f}\n\n"
        f"Бесплатные советы:\n{free_advice_text}\n\n"
        f"Категории расходов:\n{categories_text}"
    )
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_ADVICE_MODEL", "gpt-4.1-mini"),
            input=prompt,
        )
        text = (response.output_text or "").strip()
        if not text:
            return []
        result = [line.strip("•- ").strip() for line in text.splitlines() if line.strip()]
        return result[:2]
    except Exception:
        return []


def transcribe_audio_bytes(filename: str, audio_bytes: bytes) -> str:
    # Если AI-функция недоступна, возвращаем пустую строку.
    if not is_openai_available():
        return ""
    client = _get_client()
    if client is None:
        return ""
    try:
        from io import BytesIO
        file_obj = BytesIO(audio_bytes)
        file_obj.name = filename
        transcription = client.audio.transcriptions.create(
            model=os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
            file=file_obj,
        )
        return (getattr(transcription, "text", "") or "").strip()
    except Exception:
        return ""


def parse_transaction_text(text: str) -> Optional[dict]:
    # Если текста нет, сразу возвращаем пустое значение.
    if not text:
        return None
    normalized = text.strip().lower()
    if any(word in normalized for word in ["доход", "приход", "заработал", "получил"]):
        transaction_type = "income"
    elif any(word in normalized for word in ["расход", "трата", "потратил", "покупка"]):
        transaction_type = "expense"
    else:
        return None
    amount_match = re.search(r"(\d+[.,]?\d{0,2})", normalized)
    if not amount_match:
        return None
    amount = Decimal(amount_match.group(1).replace(",", ".")).quantize(Decimal("0.01"))
    date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", normalized)
    if date_match:
        try:
            operation_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        except ValueError:
            operation_date = None
    else:
        operation_date = None
    cleaned_text = normalized
    cleaned_text = re.sub(r"\b(доход|приход|заработал|получил|расход|трата|потратил|покупка)\b", "", cleaned_text)
    cleaned_text = re.sub(r"(\d+[.,]?\d{0,2})", "", cleaned_text)
    cleaned_text = re.sub(r"(\d{2}\.\d{2}\.\d{4})", "", cleaned_text)
    cleaned_text = " ".join(cleaned_text.split())
    return {
        "transaction_type": transaction_type,
        "amount": amount,
        "operation_date": operation_date,
        "raw_tail": cleaned_text,
    }
