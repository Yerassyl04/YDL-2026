"""Telegram-бот AI-консультанта фонда Шахмардана Есенова.
Поддержка языков: RU / KZ / EN.
Запуск:  python bot.py
"""
import asyncio
import logging
import re
from collections import defaultdict, deque

import requests

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

import config
from app import db, rag

logging.basicConfig(level=logging.INFO)

LANGS = ("ru", "kz", "en")
DEFAULT_LANG = "ru"

# Короткая история диалога на пользователя (для уточняющих вопросов).
HISTORY = defaultdict(lambda: deque(maxlen=6))

# ----- Локализованные подписи кнопок-вкладок -----
BTN = {
    "programs": {"ru": "📋 Программы", "kz": "📋 Бағдарламалар", "en": "📋 Programs"},
    "news": {"ru": "📰 Новости", "kz": "📰 Жаңалықтар", "en": "📰 News"},
    "contacts": {"ru": "📞 Контакты", "kz": "📞 Байланыс", "en": "📞 Contacts"},
    "start": {"ru": "🏠 Старт", "kz": "🏠 Бастау", "en": "🏠 Start"},
}
# Кнопка смены языка — одинаковая на всех языках (легко найти и распознать).
LANG_BTN = "🌐 Тіл · Язык · Language"

# ----- Локализованные тексты -----
TEXTS = {
    "ru": {
        "welcome": (
            "👋 Здравствуйте! Я AI-консультант фонда Шахмардана Есенова.\n\n"
            "Выберите раздел в меню ниже или просто задайте свой вопрос о программах, "
            "грантах, стажировках, требованиях или контактах фонда."
        ),
        "help": (
            "Выберите раздел в меню внизу (Программы, Новости, Контакты) "
            "или напишите свой вопрос обычным сообщением.\n"
            "/start — главное меню, /lang — сменить язык."
        ),
        "choose_lang": "Выберите язык:",
        "lang_set": "Язык изменён на русский ✅",
        "sources": "📎 Источники:",
        "placeholder": "Выберите раздел или задайте вопрос…",
        "error": "⚠️ Произошла ошибка при обработке запроса. Попробуйте ещё раз чуть позже.",
        "unavailable": "⏳ Сервис временно недоступен (не удалось получить ответ от ИИ). "
                       "Пожалуйста, попробуйте через минуту.",
    },
    "kz": {
        "welcome": (
            "👋 Сәлеметсіз бе! Мен Шахмардан Есенов қорының AI-кеңесшісімін.\n\n"
            "Төмендегі мәзірден бөлімді таңдаңыз немесе бағдарламалар, гранттар, "
            "тағылымдамалар, талаптар не қордың байланыстары туралы сұрағыңызды жазыңыз."
        ),
        "help": (
            "Төмендегі мәзірден бөлімді таңдаңыз (Бағдарламалар, Жаңалықтар, Байланыс) "
            "немесе сұрағыңызды жай хабарламамен жазыңыз.\n"
            "/start — басты мәзір, /lang — тілді ауыстыру."
        ),
        "choose_lang": "Тілді таңдаңыз:",
        "lang_set": "Тіл қазақшаға өзгертілді ✅",
        "sources": "📎 Дереккөздер:",
        "placeholder": "Бөлімді таңдаңыз немесе сұрақ қойыңыз…",
        "error": "⚠️ Сұрауды өңдеу кезінде қате шықты. Сәл кейінірек қайталап көріңіз.",
        "unavailable": "⏳ Қызмет уақытша қолжетімсіз (ИИ-ден жауап алынбады). "
                       "Бір минуттан кейін қайталап көріңіз.",
    },
    "en": {
        "welcome": (
            "👋 Hello! I'm the AI consultant of the Shakhmardan Yessenov Foundation.\n\n"
            "Choose a section in the menu below or simply ask your question about programs, "
            "grants, internships, requirements, or the foundation's contacts."
        ),
        "help": (
            "Choose a section in the menu below (Programs, News, Contacts) "
            "or just type your question.\n"
            "/start — main menu, /lang — change language."
        ),
        "choose_lang": "Choose a language:",
        "lang_set": "Language changed to English ✅",
        "sources": "📎 Sources:",
        "placeholder": "Choose a section or ask a question…",
        "error": "⚠️ Something went wrong while processing your request. Please try again later.",
        "unavailable": "⏳ The service is temporarily unavailable (no response from the AI). "
                       "Please try again in a minute.",
    },
}

# Канонические запросы для вкладок — всегда на русском (лучший поиск по RU-базе);
# ответ модель переводит на язык пользователя.
TAB_QUERIES = {
    "programs": (
        "Расскажи о программах фонда Есенова: гранты, стипендии, стажировки, "
        "Yessenov Data Lab, Yessenov Launch Pad, научные программы. "
        "Кратко опиши каждую программу."
    ),
    "news": "Какие последние новости и события фонда Есенова?",
    "contacts": (
        "Контакты фонда Есенова: адрес, телефон, электронная почта, "
        "официальный сайт и социальные сети. Как связаться с фондом?"
    ),
}

# Обратный поиск: подпись кнопки (на любом языке) -> ключ действия.
LABEL_TO_KEY = {BTN[key][lang]: key for key in BTN for lang in LANGS}

MAX_LEN = 3900  # запас под лимит Telegram (4096 символов на сообщение)

dp = Dispatcher()


# ============================ Утилиты ============================
def resolve_lang(user) -> str:
    """Возвращает язык пользователя. При первом входе определяет по языку Telegram."""
    lang = db.get_lang(user.id)
    if lang in LANGS:
        return lang
    code = (getattr(user, "language_code", "") or "").lower()
    lang = "kz" if code.startswith("kk") else "en" if code.startswith("en") else "ru"
    db.set_lang(user.id, lang)
    return lang


def t(lang, key) -> str:
    return TEXTS.get(lang, TEXTS[DEFAULT_LANG])[key]


def main_kb(lang) -> ReplyKeyboardMarkup:
    """Постоянная нижняя клавиатура с вкладками на нужном языке."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN["programs"][lang]), KeyboardButton(text=BTN["news"][lang])],
            [KeyboardButton(text=BTN["contacts"][lang]), KeyboardButton(text=BTN["start"][lang])],
            [KeyboardButton(text=LANG_BTN)],
        ],
        resize_keyboard=True,
        input_field_placeholder=t(lang, "placeholder"),
    )


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"),
        InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="setlang:kz"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
    ]])


def to_plain(text: str) -> str:
    """Убирает Markdown-разметку, которую Telegram не рендерит по умолчанию."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)        # **жирный**
    text = re.sub(r"__(.+?)__", r"\1", text)            # __подчёркнутый__
    text = re.sub(r"(?m)^\s*[\*\-•]\s+", "• ", text)    # маркеры списка -> •
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)       # заголовки ###
    text = re.sub(r"\*(.+?)\*", r"\1", text)            # *курсив*
    text = text.replace("`", "")                        # обратные кавычки
    text = re.sub(r"\n{3,}", "\n\n", text)              # лишние пустые строки
    return text.strip()


async def send_long(message: Message, text: str, **kwargs):
    """Отправляет текст, при необходимости разбивая на части по лимиту Telegram."""
    if len(text) <= MAX_LEN:
        await message.answer(text, **kwargs)
        return
    parts, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > MAX_LEN:
            parts.append(buf)
            buf = ""
        buf += line + "\n"
    if buf.strip():
        parts.append(buf)
    for i, part in enumerate(parts):
        # клавиатуру и прочие kwargs прикрепляем только к последней части
        await message.answer(part, **(kwargs if i == len(parts) - 1 else {}))


# ============================ Ядро ответа ============================
async def respond(message: Message, question: str, lang: str):
    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        history = list(HISTORY[message.from_user.id])
        result = await asyncio.to_thread(rag.answer, question, history, lang)

        reply = to_plain(result["answer"])
        if result["found"] and result["sources"]:
            links = "\n".join(f"• {s['title']}\n  {s['url']}" for s in result["sources"][:3])
            reply += f"\n\n{t(lang, 'sources')}\n{links}"

        await send_long(message, reply, reply_markup=main_kb(lang),
                        disable_web_page_preview=True)

        HISTORY[message.from_user.id].append({"role": "user", "content": question})
        HISTORY[message.from_user.id].append({"role": "assistant", "content": result["answer"]})

        db.log_message(
            message.from_user.id, message.from_user.username,
            message.from_user.first_name, question,
            result["answer"], result["sources"], result["found"],
        )
    except (requests.RequestException, RuntimeError):
        # Проблемы со связью/ответом alem.ai (таймаут, не-200, обрыв сети).
        logging.exception("Сервис LLM/эмбеддингов недоступен")
        await message.answer(t(lang, "unavailable"), reply_markup=main_kb(lang))
    except Exception:  # noqa: BLE001 — пользователю не должно «прилетать» молчание
        logging.exception("Непредвиденная ошибка при обработке вопроса")
        await message.answer(t(lang, "error"), reply_markup=main_kb(lang))


# ============================ Команды ============================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    lang = resolve_lang(message.from_user)
    HISTORY[message.from_user.id].clear()
    await message.answer(t(lang, "welcome"), reply_markup=main_kb(lang))


@dp.message(Command("help"))
async def cmd_help(message: Message):
    lang = resolve_lang(message.from_user)
    await message.answer(t(lang, "help"), reply_markup=main_kb(lang))


@dp.message(Command("lang"))
async def cmd_lang(message: Message):
    lang = resolve_lang(message.from_user)
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())


# ============================ Кнопки меню ============================
@dp.message(F.text == LANG_BTN)
async def btn_lang(message: Message):
    lang = resolve_lang(message.from_user)
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_kb())


@dp.message(F.text.in_(set(LABEL_TO_KEY)))
async def tabs(message: Message):
    lang = resolve_lang(message.from_user)
    key = LABEL_TO_KEY[message.text]
    if key == "start":
        HISTORY[message.from_user.id].clear()
        await message.answer(t(lang, "welcome"), reply_markup=main_kb(lang))
    else:
        await respond(message, TAB_QUERIES[key], lang)


# ============================ Смена языка (inline) ============================
@dp.callback_query(F.data.startswith("setlang:"))
async def on_setlang(callback: CallbackQuery):
    lang = callback.data.split(":", 1)[1]
    if lang not in LANGS:
        lang = DEFAULT_LANG
    db.set_lang(callback.from_user.id, lang)
    await callback.answer()
    await callback.message.answer(t(lang, "lang_set"), reply_markup=main_kb(lang))
    await callback.message.answer(t(lang, "welcome"), reply_markup=main_kb(lang))


# ============================ Любой другой текст ============================
@dp.message(F.text)
async def on_text(message: Message):
    lang = resolve_lang(message.from_user)
    question = message.text.strip()
    if question:
        await respond(message, question, lang)


@dp.error()
async def on_error(event: ErrorEvent):
    """Глобальная страховка: ловит любую ошибку, не пойманную в хендлерах,
    логирует её и пытается уведомить пользователя, чтобы бот не молчал."""
    logging.exception("Необработанная ошибка в обновлении", exc_info=event.exception)
    message = event.update.message or (
        event.update.callback_query.message if event.update.callback_query else None
    )
    user = event.update.message.from_user if event.update.message else (
        event.update.callback_query.from_user if event.update.callback_query else None
    )
    if message and user:
        lang = resolve_lang(user)
        try:
            await message.answer(t(lang, "error"), reply_markup=main_kb(lang))
        except Exception:  # noqa: BLE001 — даже уведомление может не уйти
            pass
    return True


async def main():
    db.init_db()
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN не задан в .env")

    index, _ = rag.vectorstore.load_index()
    if index is None:
        logging.warning("База знаний пуста — сначала выполните: python -m app.ingest")

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    logging.info("🤖 Бот запущен. Ожидание сообщений…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
