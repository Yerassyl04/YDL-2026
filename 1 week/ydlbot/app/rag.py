"""RAG-ядро: поиск релевантного контекста + генерация ответа с жёстким заземлением."""
import config
from app import llm, vectorstore

# Локализованный ответ «не найдено» по языкам.
NOT_FOUND = {
    "ru": "Я не нашёл этой информации в материалах фонда.",
    "kz": "Мен бұл ақпаратты қордың материалдарынан таппадым.",
    "en": "I could not find this information in the foundation's materials.",
}

# На каком языке модель должна отвечать.
LANG_NAME = {
    "ru": "русском",
    "kz": "казахском (қазақ тілінде)",
    "en": "английском (in English)",
}


def _system_prompt(lang):
    nf = NOT_FOUND.get(lang, NOT_FOUND["ru"])
    lang_name = LANG_NAME.get(lang, LANG_NAME["ru"])
    return (
        "Ты — официальный AI-консультант фонда Шахмардана Есенова (Yessenov Foundation).\n"
        "Отвечай ТОЛЬКО на основе приведённого ниже КОНТЕКСТА из официальных материалов фонда.\n"
        "Правила:\n"
        f"- Если в КОНТЕКСТЕ нет данных для ответа — ответь ДОСЛОВНО: «{nf}»\n"
        "- Категорически запрещено выдумывать дедлайны, суммы грантов, требования, даты, "
        "имена и контакты, которых нет в КОНТЕКСТЕ.\n"
        "- Не используй знания за пределами КОНТЕКСТА.\n"
        f"- Отвечай СТРОГО на {lang_name} языке, независимо от языка вопроса и контекста.\n"
        "- Не упоминай слово «контекст» в ответе — просто отвечай как консультант фонда.\n"
        "- НЕ используй Markdown-разметку (никаких **, *, #, _, `). "
        "Пиши обычным текстом. Для списков ставь в начале строки символ «•»."
    )

_index = None
_chunks = None


def _ensure_loaded():
    global _index, _chunks
    if _index is None:
        _index, _chunks = vectorstore.load_index()
    return _index is not None


def reload_index():
    """Перечитать индекс из файлов (после обновления базы знаний)."""
    global _index, _chunks
    _index, _chunks = vectorstore.load_index()


def retrieve(question):
    if not _ensure_loaded():
        return []
    qvec = llm.embed(question)[0]
    return vectorstore.search(_index, _chunks, qvec, config.TOP_K)


def _build_context(results):
    blocks = []
    for i, r in enumerate(results, 1):
        blocks.append(f"[Источник {i}] {r['title']}\nURL: {r['url']}\n{r['text']}")
    return "\n\n---\n\n".join(blocks)


def answer(question, history=None, lang="ru"):
    """Главная точка входа. Возвращает {answer, sources, found}."""
    results = retrieve(question)
    relevant = [r for r in results if r["score"] >= config.MIN_SCORE]

    if not relevant:
        return {"answer": NOT_FOUND.get(lang, NOT_FOUND["ru"]), "sources": [], "found": False}

    context = _build_context(relevant)
    messages = [{"role": "system", "content": _system_prompt(lang)}]
    if history:
        messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"КОНТЕКСТ:\n{context}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}",
    })

    text = llm.chat(messages)

    # Если модель всё же ответила отказом — приводим к единому виду «не найдено»
    # (без ложных источников и с корректным флагом для логов/админки).
    nf = NOT_FOUND.get(lang, NOT_FOUND["ru"])
    if text.strip().rstrip(".!").lower() == nf.strip().rstrip(".!").lower():
        return {"answer": nf, "sources": [], "found": False}

    # уникальные источники с сохранением порядка
    seen, sources = set(), []
    for r in relevant:
        if r["url"] not in seen:
            seen.add(r["url"])
            sources.append({"title": r["title"], "url": r["url"], "score": round(r["score"], 3)})

    return {"answer": text, "sources": sources, "found": True}
