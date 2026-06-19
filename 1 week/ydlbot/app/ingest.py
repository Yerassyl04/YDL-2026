"""Пайплайн наполнения базы знаний:
скрейпинг -> чанкинг -> эмбеддинги -> FAISS-индекс.
Запуск напрямую:  python -m app.ingest
"""
import json
from datetime import datetime

import config
from app import chunker, llm, scraper, vectorstore


def run_ingest(progress=None):
    """Полностью пересобирает базу знаний. progress(str) — колбэк для логов."""
    def report(msg):
        if progress:
            progress(msg)
        else:
            
            print(msg)

    report("🌐 Скрейпинг сайта…")
    docs = scraper.scrape_site(progress=lambda n, u: report(f"   [{n}] {u}"))
    report(f"📄 Собрано страниц: {len(docs)}")

    chunks = []
    for d in docs:
        for piece in chunker.split_text(d["text"], config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append({"text": piece, "url": d["url"], "title": d["title"]})
    report(f"✂️  Создано чанков: {len(chunks)}")

    if not chunks:
        report("⚠️  Нет данных для индексации. Проверьте SCRAPE_BASE_URL.")
        return {"docs": 0, "chunks": 0, "updated_at": None}

    report("🧮 Создание эмбеддингов…")
    vectors = llm.embed([c["text"] for c in chunks])

    report("🗂️  Построение FAISS-индекса…")
    vectorstore.build_index(vectors, chunks)

    meta = {
        "docs": len(docs),
        "chunks": len(chunks),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": config.SCRAPE_BASE_URL,
    }
    with open(config.KB_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    report("✅ База знаний готова.")
    return meta


if __name__ == "__main__":
    run_ingest()
